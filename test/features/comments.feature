@comments
Feature: Comments

    Scenario: The Add Comment form should not display for a non-logged-in user - instead they see a 'Login to comment' button
        Given "Unauthenticated" as the persona
        When I go to dataset "warandpeace" comments
        Then I should see "Login to comment" within 1 seconds
        And I should not see the add comment form

    Scenario: Logged-in users see the add comment form
        Given "CKANUser" as the persona
        When I log in
        Then I go to dataset "warandpeace" comments
        Then I should see the add comment form

    @comment-add
    Scenario: When a logged-in user submits a comment on a Dataset the comment should display within 10 seconds
        Given "CKANUser" as the persona
        When I log in
        Then I go to dataset "warandpeace" comments
        Then I should see the add comment form
        Then I submit a comment with subject "Test subject" and comment "This is a test comment"
        Then I should see "This is a test comment" within 10 seconds
        And I should see an element with xpath "//div[contains(@class, 'comment-wrapper') and contains(string(), 'This is a test comment')]"

    @comment-add @comment-profane
    Scenario: When a logged-in user submits a comment containing whitelisted profanity on a Dataset the comment should display within 10 seconds
        Given "CKANUser" as the persona
        When I log in
        Then I go to dataset "warandpeace" comments
        Then I should see the add comment form
        Then I submit a comment with subject "Test subject" and comment "sex"
        Then I should see "sex" within 10 seconds

    @comment-report
    Scenario: When a logged-in user reports a comment on a Dataset the comment should be marked as reported and an email sent to the admins of the organisation
        Given "CKANUser" as the persona
        When I log in
        Then I go to dataset "warandpeace" comments
        And I press the element with xpath "//a[contains(string(), 'Report')]"
        Then I should see "Reported" within 5 seconds
        When I wait for 3 seconds
        Then I should receive a base64 email at "test_org_admin@localhost" containing "This comment has been flagged as inappropriate by a user"

    @comment-reply
    Scenario: When a logged-in user submits a reply comment on a Dataset, the comment should display within 10 seconds
        Given "CKANUser" as the persona
        When I log in
        Then I go to dataset "warandpeace" comments
        Then I take a screenshot
        Then I submit a reply with comment "This is a reply"
        Then I should see "This is a reply" within 10 seconds

    @comment-delete
    Scenario: When an Org Admin visits a dataset belonging to their organisation, they can delete a comment and should see deletion text for the user responsible.
        Given "TestOrgAdmin" as the persona
        When I log in
        Then I go to dataset "warandpeace" comments
        And I press the element with xpath "//a[contains(@href, '/delete')]"
        Then I should see "This comment was deleted." within 2 seconds

    @comment-tab
    Scenario: Non-logged in users should not see comment form in dataset tab
        Given "Unauthenticated" as the persona
        When I go to dataset "warandpeace"
        Then I should not see an element with id "comment_form"

    @comment-tab
    Scenario: Logged in users should not see comment form in dataset tab
        Given "CKANUser" as the persona
        When I go to dataset "warandpeace"
        Then I should not see an element with id "comment_form"

    @comment-tab
    Scenario: Users should see comment tab on dataset
        Given "Unauthenticated" as the persona
        Then I go to dataset "warandpeace"
        Then I should see an element with xpath "//a[contains(string(), 'Comments')]"

    @comment-tab
    Scenario: Users should see comment badge count of 2 on dataset
        Given "Unauthenticated" as the persona
        Then I go to dataset "warandpeace"
        Then I should see an element with xpath "//span[contains(@class, 'badge') and contains(string(), '2')]"
