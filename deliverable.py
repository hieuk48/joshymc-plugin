from typing import Dict, List, Optional, Tuple

class StaffRank:
    """Represents staff ranks with permission levels."""
    RANKS = {
        'helper': 1,
        'mod': 2,
        'admin': 3,
        'owner': 4,
    }

    @classmethod
    def has_permission(cls, staff_rank: str, required_rank: str) -> bool:
        """
        Check if staff_rank has permission equal or higher than required_rank.
        """
        return cls.RANKS.get(staff_rank, 0) >= cls.RANKS.get(required_rank, 0)

class PunishmentTier:
    """
    Represents a single punishment tier.
    """
    def __init__(self, action: str, duration_minutes: Optional[int], message: str):
        self.action = action  # e.g., 'warn', 'mute', 'kick', 'tempban', 'ban'
        self.duration_minutes = duration_minutes  # None for permanent actions
        self.message = message

    def __repr__(self) -> str:
        return (f"PunishmentTier(action={self.action!r}, "
                f"duration_minutes={self.duration_minutes!r}, message={self.message!r})")

class RuleEscalation:
    """
    Holds the escalation tiers for a specific rule.
    """
    def __init__(self, rule_keyword: str, tiers: List[PunishmentTier], min_staff_rank: str):
        self.rule_keyword = rule_keyword  # e.g., 'spam-messages'
        self.tiers = tiers  # List of PunishmentTier, in escalation order
        self.min_staff_rank = min_staff_rank  # e.g., 'mod'

    def get_tier(self, offense_count: int) -> PunishmentTier:
        """
        Get the punishment tier for the given offense count (1-based).
        If offense_count exceeds tiers, return the last tier.
        """
        idx = min(offense_count - 1, len(self.tiers) - 1)
        return self.tiers[idx]

class PunishmentHistory:
    """
    Tracks player punishments for each rule.
    """
    def __init__(self):
        # player_name -> rule_keyword -> count
        self.history: Dict[str, Dict[str, int]] = {}

    def record_offense(self, player: str, rule_keyword: str) -> int:
        """
        Increment and return the new offense count for the player and rule.
        """
        if player not in self.history:
            self.history[player] = {}
        if rule_keyword not in self.history[player]:
            self.history[player][rule_keyword] = 0
        self.history[player][rule_keyword] += 1
        return self.history[player][rule_keyword]

    def get_offense_count(self, player: str, rule_keyword: str) -> int:
        """
        Get the current offense count for the player and rule.
        """
        return self.history.get(player, {}).get(rule_keyword, 0)

class PunishCommandHandler:
    """
    Handles the /punish command with five-tier escalation, hyphenated rule keywords, and staff rank permissions.
    """
    def __init__(self, rules: Dict[str, RuleEscalation], punishment_history: PunishmentHistory):
        self.rules = rules
        self.punishment_history = punishment_history

    def punish(self, staff: str, staff_rank: str, player: str, rule_keyword: str) -> Tuple[bool, str]:
        """
        Process the /punish command.
        Returns (success, message).
        """
        rule = self.rules.get(rule_keyword)
        if not rule:
            return False, f"Unknown rule: '{rule_keyword}'."

        if not StaffRank.has_permission(staff_rank, rule.min_staff_rank):
            return False, (f"Insufficient permissions. '{rule_keyword}' requires at least "
                           f"{rule.min_staff_rank} rank.")

        offense_count = self.punishment_history.record_offense(player, rule_keyword)
        tier = rule.get_tier(offense_count)

        # Simulate punishment action (in real plugin, would call server API)
        action_msg = self._format_action_message(tier, player, rule_keyword, offense_count)
        return True, action_msg

    def _format_action_message(self, tier: PunishmentTier, player: str, rule_keyword: str, offense_count: int) -> str:
        """
        Formats the punishment action message.
        """
        duration = (f"{tier.duration_minutes} minutes" if tier.duration_minutes is not None else "permanent")
        return (f"[{rule_keyword}] Offense #{offense_count}: {tier.action.upper()} {player} "
                f"for {duration}. Reason: {tier.message}")

# Example rules configuration
def get_default_rules() -> Dict[str, RuleEscalation]:
    """
    Returns default rules with five-tier escalation and hyphenated keywords.
    """
    return {
        'spam-messages': RuleEscalation(
            rule_keyword='spam-messages',
            min_staff_rank='helper',
            tiers=[
                PunishmentTier('warn', None, 'Please do not spam messages.'),
                PunishmentTier('mute', 10, 'Muted for spamming messages.'),
                PunishmentTier('mute', 60, 'Muted for repeated spamming.'),
                PunishmentTier('kick', None, 'Kicked for continued spamming.'),
                PunishmentTier('tempban', 1440, 'Banned for persistent spamming.'),  # 1 day
            ]
        ),
        'inappropriate-language': RuleEscalation(
            rule_keyword='inappropriate-language',
            min_staff_rank='mod',
            tiers=[
                PunishmentTier('warn', None, 'Please avoid inappropriate language.'),
                PunishmentTier('mute', 30, 'Muted for inappropriate language.'),
                PunishmentTier('mute', 120, 'Muted for repeated inappropriate language.'),
                PunishmentTier('kick', None, 'Kicked for continued inappropriate language.'),
                PunishmentTier('ban', None, 'Permanently banned for persistent inappropriate language.'),
            ]
        ),
        'cheating-hacks': RuleEscalation(
            rule_keyword='cheating-hacks',
            min_staff_rank='admin',
            tiers=[
                PunishmentTier('warn', None, 'Cheating is not allowed.'),
                PunishmentTier('kick', None, 'Kicked for suspected cheating.'),
                PunishmentTier('tempban', 4320, 'Banned for cheating (3 days).'),
                PunishmentTier('tempban', 10080, 'Banned for repeated cheating (7 days).'),
                PunishmentTier('ban', None, 'Permanently banned for persistent cheating.'),
            ]
        ),
    }

# --- TESTS ---

def _test_punish_command_handler():
    """
    Test the PunishCommandHandler for correct escalation and permissions.
    """
    rules = get_default_rules()
    history = PunishmentHistory()
    handler = PunishCommandHandler(rules, history)

    # Staff with insufficient rank
    success, msg = handler.punish('Alice', 'helper', 'Bob', 'cheating-hacks')
    assert not success and 'Insufficient permissions' in msg

    # Unknown rule
    success, msg = handler.punish('Alice', 'admin', 'Bob', 'unknown-rule')
    assert not success and 'Unknown rule' in msg

    # Escalation for spam-messages
    for i in range(1, 7):
        success, msg = handler.punish('Alice', 'helper', 'Bob', 'spam-messages')
        assert success
        if i == 1:
            assert 'WARN' in msg and 'Offense #1' in msg
        elif i == 2:
            assert 'MUTE' in msg and '10 minutes' in msg
        elif i == 3:
            assert 'MUTE' in msg and '60 minutes' in msg
        elif i == 4:
            assert 'KICK' in msg
        elif i >= 5:
            assert 'TEMPBAN' in msg and '1440 minutes' in msg

    # Escalation for inappropriate-language, staff rank check
    for i in range(1, 7):
        success, msg = handler.punish('Eve', 'mod', 'Charlie', 'inappropriate-language')
        assert success
        if i == 1:
            assert 'WARN' in msg
        elif i == 2:
            assert 'MUTE' in msg and '30 minutes' in msg
        elif i == 3:
            assert 'MUTE' in msg and '120 minutes' in msg
        elif i == 4:
            assert 'KICK' in msg
        elif i >= 5:
            assert 'BAN' in msg and 'permanent' in msg

    # Cheating-hacks, admin required
    for i in range(1, 7):
        success, msg = handler.punish('Zed', 'admin', 'Hacker', 'cheating-hacks')
        assert success
        if i == 1:
            assert 'WARN' in msg
        elif i == 2:
            assert 'KICK' in msg
        elif i == 3:
            assert 'TEMPBAN' in msg and '4320 minutes' in msg
        elif i == 4:
            assert 'TEMPBAN' in msg and '10080 minutes' in msg
        elif i >= 5:
            assert 'BAN' in msg and 'permanent' in msg

if __name__ == "__main__":
    _test_punish_command_handler()