try:
    import ckan.plugins.toolkit as tk

    ckanext = tk.signals.ckanext
except AttributeError:
    from blinker import Namespace

    ckanext = Namespace()

created = ckanext.signal("comments:created")
"""Sent when a new comment created.
Params:
    sender: Thread ID
    comment: comment dictionary
"""

updated = ckanext.signal("comments:updated")
"""Sent after an update of exisning comment.
Params:
    sender: Thread ID
    comment: comment dictionary
"""

deleted = ckanext.signal("comments:deleted")
"""Sent when a comment is deleted.
Params:
    sender: Thread ID
    comment: comment dictionary
"""
