import unittest

from discord_setup import (
    GUILD_ID, Scope, ScopeError, Setup, changed_fields, effective_permissions, validate_access,
    role_is_higher, welcome_image,
)


class IsolationTests(unittest.TestCase):
    def test_cross_server_and_unknown_channel_requests_are_rejected(self):
        scope = Scope(["100"])
        forbidden = [
            ("GET", "/guilds/999/channels", None),
            ("PATCH", "/guilds/999", {"name": "Wrong"}),
            ("POST", "/channels/999/messages", {"content": "Wrong"}),
            ("GET", "https://example.com/", None),
            ("GET", "/guilds/1552483229649477767/../999", None),
            ("GET", "/guilds/1552483229649477767%2f..%2f999", None),
            ("DELETE", "/channels/100", None),
            ("POST", "/users/@me/channels", {"recipient_id": "999"}),
            ("PATCH", "/channels/100", {"parent_id": "999"}),
            ("PATCH", "/applications/@me", {"description": "Out of scope"}),
        ]
        for method, path, body in forbidden:
            with self.subTest(method=method, path=path):
                with self.assertRaises(ScopeError):
                    scope.authorize(method, path, body)

    def test_target_server_and_verified_channel_requests_are_allowed(self):
        scope = Scope(["100", "101"])
        for method, path, body in [
            ("GET", "/users/@me", None),
            ("GET", "/applications/@me", None),
            ("GET", "/users/@me/guilds?limit=200", None),
            ("GET", "/guilds/1552483229649477767/channels", None),
            ("POST", "/guilds/1552483229649477767/roles", {"name": "Member"}),
            ("PATCH", "/channels/100", {"parent_id": "101"}),
            ("POST", "/channels/100/messages", {"content": "Welcome"}),
        ]:
            scope.authorize(method, path, body)

    def test_extra_installations_public_bots_and_missing_admin_are_rejected(self):
        identity = {"bot": True, "id": "123"}
        private = {"bot_public": False, "id": "123"}
        target = {"id": GUILD_ID, "permissions": "8"}
        for who, app, guilds in [
            (identity, private, []),
            (identity, private, [target, {"id": "999", "permissions": "8"}]),
            (identity, {"bot_public": True, "id": "123"}, [target]),
            ({"bot": False, "id": "123"}, private, [target]),
            (identity, private, [{"id": GUILD_ID, "permissions": "1024"}]),
            (identity, private, [{"id": "999", "permissions": "8"}]),
        ]:
            with self.subTest(who=who, app=app, guilds=guilds):
                with self.assertRaises(ScopeError):
                    validate_access(who, app, guilds)
        validate_access(identity, private, [target])


class ReconciliationTests(unittest.TestCase):
    def test_only_actual_changes_are_written(self):
        current = {"name": "general", "topic": "Old", "id": "100", "type": 0}
        self.assertEqual(changed_fields(current, {"name": "general", "topic": "New"}), {"topic": "New"})
        self.assertEqual(changed_fields(current, {"name": "general"}), {})

    def test_overwrite_order_and_string_permission_numbers_do_not_cause_repeat_changes(self):
        current = {"permission_overwrites": [
            {"id": "200", "type": 0, "allow": "1024", "deny": "0"},
            {"id": GUILD_ID, "type": 0, "allow": "0", "deny": "1024"},
        ]}
        desired = {"permission_overwrites": [
            {"id": GUILD_ID, "type": 0, "allow": 0, "deny": 1024},
            {"id": "200", "type": 0, "allow": 1024, "deny": 0},
        ]}
        self.assertEqual(changed_fields(current, desired), {})


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.roles = [
            {"id": GUILD_ID, "permissions": "3072"},
            {"id": "contributor", "permissions": "0"},
            {"id": "moderator", "permissions": "8192"},
            {"id": "bot", "permissions": "8"},
        ]
        self.staff = [
            {"id": GUILD_ID, "type": 0, "allow": "0", "deny": "1024"},
            {"id": "moderator", "type": 0, "allow": "1024", "deny": "0"},
        ]

    def test_staff_rooms_hidden_from_regular_and_interest_roles(self):
        for role_ids in [[], ["contributor"]]:
            self.assertFalse(effective_permissions(self.roles, role_ids, self.staff) & 1024)
        self.assertTrue(effective_permissions(self.roles, ["moderator"], self.staff) & 1024)
        self.assertTrue(effective_permissions(self.roles, ["bot"], self.staff) & 1024)

    def test_read_only_channels_deny_posting_but_preserve_read_access(self):
        overwrites = [
            {"id": GUILD_ID, "type": 0, "allow": "0", "deny": "2048"},
            {"id": "moderator", "type": 0, "allow": "2048", "deny": "0"},
        ]
        ordinary = effective_permissions(self.roles, ["contributor"], overwrites)
        self.assertTrue(ordinary & 1024)
        self.assertFalse(ordinary & 2048)
        self.assertTrue(effective_permissions(self.roles, ["moderator"], overwrites) & 2048)


class OnboardingTests(unittest.TestCase):
    def prepare(self, current):
        class Endpoint:
            sent = None

            def request(self, method, path, body=None):
                if method == "GET":
                    return current
                self.sent = body
                return body

        setup = Setup.__new__(Setup)
        setup.api = Endpoint()
        setup.state = {"channels": {key: str(i + 100) for i, key in enumerate((
            "welcome", "rules", "general", "introductions", "showcase", "suggestions", "matchmaking", "training", "modding", "bugs", "help"))},
            "roles": {"Player": "201", "Modder": "202", "Playtester": "203"}}
        setup.save = lambda: None
        return setup

    def test_new_onboarding_question_and_answers_include_required_ids(self):
        setup = self.prepare({"prompts": [], "enabled": False, "default_channel_ids": [], "mode": 0})
        setup.onboarding()
        prompt = setup.api.sent["prompts"][0]
        self.assertRegex(str(prompt.get("id", "")), r"^[0-9]+$")
        ids = [prompt["id"]] + [o.get("id") for o in prompt["options"]]
        self.assertTrue(all(v is not None for v in ids))
        self.assertEqual(len(set(ids)), 4)

    def test_reconfiguring_onboarding_keeps_discord_assigned_ids(self):
        current = {"prompts": [{"id": "900", "title": "What brings you to GD's Melee?", "options": [
            {"id": "901", "title": "Play and practice"},
            {"id": "902", "title": "Make mods and scripts"},
            {"id": "903", "title": "Test and report bugs"},
        ]}]}
        setup = self.prepare(current)
        setup.onboarding()
        prompt = setup.api.sent["prompts"][0]
        self.assertEqual([prompt["id"]] + [o["id"] for o in prompt["options"]], ["900", "901", "902", "903"])


class LiveResponseTests(unittest.TestCase):
    def test_equal_role_positions_use_discord_snowflake_tiebreak(self):
        older = {"id": "100", "position": 1}
        newer = {"id": "200", "position": 1}
        self.assertTrue(role_is_higher(older, newer))
        self.assertFalse(role_is_higher(newer, older))
        self.assertTrue(role_is_higher({"id": "300", "position": 2}, older))

    def test_embed_only_attachment_is_recognized_without_reupload(self):
        url = "https://cdn.discordapp.com/attachments/100/200/welcome.png"
        live = {"attachments": [], "embeds": [{"image": {"url": url, "width": 960, "height": 540}}]}
        self.assertEqual(welcome_image(live), {"url": url})
        self.assertIsNone(welcome_image({"attachments": [], "embeds": [{"title": "Welcome"}]}))


if __name__ == "__main__":
    unittest.main()
