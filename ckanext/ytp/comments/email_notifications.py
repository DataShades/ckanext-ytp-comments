# encoding: utf-8

import logging

from ckan import authz, model
from ckan.lib import maintain
from ckan.lib.mailer import mail_recipient, MailerException
from ckan.plugins.toolkit import config, enqueue_job, get_action, \
    get_or_bust, render, ObjectNotFound

from . import helpers, notification_helpers, util


log1 = logging.getLogger(__name__)


def get_member_list(context, data_dict=None):
    '''
    :param id: the id or name of the group
    :type id: string
    :param object_type: restrict the members returned to those of a given type,
      e.g. ``'user'`` or ``'package'`` (optional, default: ``None``)
    :type object_type: string
    :param capacity: restrict the members returned to those with a given
      capacity, e.g. ``'member'``, ``'editor'``, ``'admin'``, ``'public'``,
      ``'private'`` (optional, default: ``None``)
    :type capacity: string

    :rtype: list of (id, type, capacity) tuples

    :raises: :class:`ckan.logic.ObjectNotFound`: if the group doesn't exist

    '''
    model = context['model']

    group = model.Group.get(get_or_bust(data_dict, 'id'))
    if not group:
        raise ObjectNotFound

    obj_type = data_dict.get('object_type', None)
    capacity = data_dict.get('capacity', None)

    q = model.Session.query(model.Member).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == "active")

    if obj_type:
        q = q.filter(model.Member.table_name == obj_type)
    if capacity:
        q = q.filter(model.Member.capacity == capacity)

    trans = authz.roles_trans()

    def translated_capacity(capacity):
        try:
            return trans[capacity]
        except KeyError:
            return capacity

    return [(m.table_id, m.table_name, translated_capacity(m.capacity))
            for m in q.all()]


def get_users_for_org_by_capacity(owner_org, capacity, excluded_emails=[]):
    """
    Returns a list of user email addresses in the supplied organisation ID, for a given capacity

    :param owner_org: string
    :param capacity: string
    :param excluded_emails: list of email addresses to exclude
    :return: list of user email addresses
    """
    users = []

    member_list = get_member_list(
        {'model': model},
        {
            'id': owner_org,
            'object_type': 'user',
            'capacity': capacity
        })

    for member in member_list:
        user = model.User.get(member[0])
        if user and user.email and user.email not in excluded_emails:
            users.append(user.email)

    return users


def get_dataset_author_email(dataset_id):
    """
    Returns the email address of the dataset author
    :param dataset_id: string
    :return: string of dataset author email address
    """
    context = {'model': model}
    dataset = get_action('package_show')(context, {'id': dataset_id})

    return dataset.get('author_email', None) if dataset else None


def send_email(to, subject, msg):
    """
    Use CKAN mailer logic to send an email to an individual email address

    :param to: string
    :param subject: string
    :param msg: string
    :return:
    """
    # Attempt to send mail.
    mail_dict = {
        'recipient_email': to,
        'recipient_name': to,
        'subject': subject,
        'body': msg,
        'headers': {'reply-to': config.get('smtp.mail_from')}
    }

    try:
        mail_recipient(**mail_dict)
    except MailerException:
        log1.error(u'Cannot send email notification to %s.', to, exc_info=1)


def send_notification_emails(users, template, extra_vars):
    """
    Sets the email body and sends an email notification to each user in the list provided

    :param users: list of user email addresses to receive the notification
    :param template: string indicating which email template to use
    :param extra_vars: dict
    :return:
    """
    if users:
        subject = render('emails/subjects/{0}.txt'.format(template), extra_vars)
        body = render('emails/bodies/{0}.txt'.format(template), extra_vars)

        for user in users:
            enqueue_job(send_email, [user, subject, body], title=u'Comment Email')


def get_admins(owner_org, user, content_type, content_item_id):
    if content_type == 'datarequest':
        # Get all the org admin users (excluding the user who made the comment)
        users = get_users_for_org_by_capacity(owner_org, 'admin', [user.email])
    else:
        try:
            author_email = get_dataset_author_email(content_item_id)
            users = [author_email] if author_email else []
        except ObjectNotFound:
            log1.warn("No accounts found to notify for %s: %s",
                      content_type, content_item_id)
            users = []
    return users


@maintain.deprecated('notify_admins is deprecated please use notify_admins_and_comment_notification_recipients')
def notify_admins(owner_org, user, template, content_type, content_item_id, comment_id):
    """
    Warning: this function has been deprecated - please use `notify_admins_and_comment_notification_recipients`
    :param owner_org: organization.id of the content item owner
    :param user: c.user_obj of the user who submitted the comment
    :param template: string indicating which email template to use
    :param content_type: string dataset or datarequest
    :param content_item_id: UUID of the content item
    :param comment_id: ID of the comment submitted (used in URL of email body)
    :return:
    """
    admin_users = get_admins(owner_org, user, content_type, content_item_id)

    if admin_users:
        send_notification_emails(
            admin_users,
            template,
            {
                'url': helpers.get_content_item_link(content_type, content_item_id, comment_id)
            }
        )


def notify_admins_and_comment_notification_recipients(owner_org, user, template, content_type, content_item_id, thread_id, parent_id, comment_id, content_item_title, comment):

    admin_users = get_admins(owner_org, user, content_type, content_item_id)

    if notification_helpers.comment_notification_recipients_enabled():
        # Get email addresses for all users following the content item (excluding user who made the comment)
        content_item_followers = notification_helpers.get_content_item_followers(user.email, thread_id)

        if parent_id:
            # Get email addresses for all users following the top level comment (excluding user who made the comment)
            top_level_comment_followers = notification_helpers.get_top_level_comment_followers(user.email, thread_id, parent_id)
        else:
            top_level_comment_followers = []

    if notification_helpers.comment_notification_recipients_enabled():
        # Combine all lists
        users = list(set(admin_users + content_item_followers + top_level_comment_followers))

        # Remove any users who have specifically muted the thread
        if parent_id:
            top_level_comment_mutees = notification_helpers.get_top_level_comment_mutees(thread_id, parent_id)
            for mutee in top_level_comment_mutees:
                if mutee in users:
                    try:
                        users.remove(mutee)
                    except ValueError:
                        continue
    else:
        users = list(set(admin_users))

    if users:
        send_notification_emails(
            users,
            template,
            {
                'url': helpers.get_content_item_link(content_type, content_item_id, comment_id),
                'content_item_title': util.remove_HTML_markup(content_item_title),
                'comment_text': util.remove_HTML_markup(comment),
                'content_type': content_type
            }
        )


def get_content_type_and_org_id(context, thread_url, content_item_id):
    """
    Derives the content type and ID of the owning organisation from the comment thread URL and the content item ID

    :param context:
    :param thread_url:
    :param content_item_id:
    :return:
    """
    org_id = None
    data_dict = {'id': content_item_id}
    try:
        if thread_url.find('datarequest') != -1:
            content_type = 'datarequest'
            action = 'show_datarequest'
        else:
            content_type = 'dataset'
            action = 'package_show'
        content_item = get_action(action)(context, data_dict)
        if content_item:
            org_id = content_item['organization_id'] if content_type == 'datarequest' else content_item['owner_org']
    except ObjectNotFound:
        log1.error('Content item (%s) with ID %s not found' % (content_type, content_item_id))

    return content_type, org_id


def flagged_comment_notification(comment):
    """
    Determines the organisation of the content item the comment belongs to and sends email notifications

    :param comment: comment object
    :return:
    """
    context = {'model': model}
    thread = get_action('thread_show')(context, {'id': comment.thread_id})

    if thread:
        # Last fragment contains the UUID of the content item
        content_item_id = thread['url'].split("/")[-1]
        # Derive content type from `thread`.`url`
        content_type, org_id = get_content_type_and_org_id(
            context,
            thread['url'],
            content_item_id
        )

        if content_type and org_id:
            # Email the org admin users of the content item being commented on
            send_notification_emails(
                get_users_for_org_by_capacity(org_id, 'admin'),
                'notification-flagged-comment',
                {
                    'url': helpers.get_content_item_link(content_type, content_item_id, comment.id)
                }
            )
