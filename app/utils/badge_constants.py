"""
Badge Constants and Definitions
Central location for all badge-related constants
"""

from typing import List, NamedTuple, Optional
from decimal import Decimal
from enum import Enum


class BadgeType(str, Enum):
    """Badge type enumeration"""
    RISING_STAR = "rising_star"
    EMERGING_CREATOR = "emerging_creator"
    PROVEN_PERFORMER = "proven_performer"
    TOP_CREATOR = "top_creator"
    ELITE_PERFORMER = "elite_performer"
    CREATOR_LEGEND = "creator_legend"
    HALL_OF_FAME = "hall_of_fame"


class BadgeTier(NamedTuple):
    """Badge tier definition"""
    badge_type: str
    name: str
    tier: str
    description: str
    gmv_threshold: Decimal
    icon: str
    color: str
    bg_color: str
    benefits: List[str]


# Badge tier definitions matching the UI
BADGE_TIERS: List[BadgeTier] = [
    BadgeTier(
        badge_type=BadgeType.RISING_STAR,
        name="Rising Star",
        tier="Bronze",
        description="You're just getting started on your creator journey!",
        gmv_threshold=Decimal("1000"),
        icon="Star",
        color="text-amber-600",
        bg_color="bg-amber-600/20",
        benefits=[
            "Access to beginner campaigns",
            "Basic creator resources",
            "Community forum access"
        ]
    ),
    BadgeTier(
        badge_type=BadgeType.EMERGING_CREATOR,
        name="Emerging Creator",
        tier="Silver",
        description="Your content is gaining traction and driving sales!",
        gmv_threshold=Decimal("5000"),
        icon="TrendingUp",
        color="text-green-500",
        bg_color="bg-green-500/20",
        benefits=[
            "Priority campaign access",
            "Performance analytics",
            "Dedicated support channel"
        ]
    ),
    BadgeTier(
        badge_type=BadgeType.PROVEN_PERFORMER,
        name="Proven Performer",
        tier="Gold",
        description="You've proven your ability to drive consistent sales!",
        gmv_threshold=Decimal("10000"),
        icon="Award",
        color="text-yellow-500",
        bg_color="bg-yellow-500/20",
        benefits=[
            "Premium campaign opportunities",
            "Higher commission rates",
            "Monthly performance bonuses",
            "Advanced analytics dashboard"
        ]
    ),
    BadgeTier(
        badge_type=BadgeType.TOP_CREATOR,
        name="Top Creator",
        tier="Platinum",
        description="You're among the top performers in our network!",
        gmv_threshold=Decimal("50000"),
        icon="Gem",
        color="text-blue-400",
        bg_color="bg-blue-400/20",
        benefits=[
            "Exclusive brand partnerships",
            "Custom campaign opportunities",
            "Quarterly bonus program",
            "Priority payout processing"
        ]
    ),
    BadgeTier(
        badge_type=BadgeType.ELITE_PERFORMER,
        name="Elite Performer",
        tier="Diamond",
        description="You're in the elite tier of content creators!",
        gmv_threshold=Decimal("100000"),
        icon="Zap",
        color="text-purple-400",
        bg_color="bg-purple-400/20",
        benefits=[
            "VIP brand access",
            "Negotiable rates",
            "Annual performance rewards",
            "Dedicated account manager",
            "Early access to new features"
        ]
    ),
    BadgeTier(
        badge_type=BadgeType.CREATOR_LEGEND,
        name="Creator Legend",
        tier="Master",
        description="You've achieved legendary status in our creator community!",
        gmv_threshold=Decimal("500000"),
        icon="Crown",
        color="text-orange-400",
        bg_color="bg-orange-400/20",
        benefits=[
            "Top-tier commission rates",
            "Direct brand collaboration",
            "Equity partnership opportunities",
            "Speaking opportunities",
            "Mentorship program access"
        ]
    ),
    BadgeTier(
        badge_type=BadgeType.HALL_OF_FAME,
        name="Hall of Fame",
        tier="Legendary",
        description="You're in the Creator Hall of Fame - an inspiration to all!",
        gmv_threshold=Decimal("1000000"),
        icon="Trophy",
        color="text-yellow-300",
        bg_color="bg-gradient-to-r from-yellow-400/20 to-yellow-600/20",
        benefits=[
            "Lifetime achievement recognition",
            "Maximum commission rates",
            "Strategic partnership opportunities",
            "Annual hall of fame event",
            "Legacy creator status",
            "Co-creation opportunities with brands"
        ]
    )
]


# Badge display configuration
BADGE_DISPLAY_CONFIG = {
    "max_featured_badges": 3,  # Maximum badges to show in profile showcase
    "leaderboard_page_size": 20,  # Default page size for leaderboards
    "progress_calculation_lookback_days": 30,  # Days to look back for pace calculation
    "notification_cooldown_hours": 24,  # Hours between badge notifications
}


# Badge-related messages
BADGE_MESSAGES = {
    "achievement": {
        BadgeType.RISING_STAR: "Welcome to the creator community! You've earned your first badge!",
        BadgeType.EMERGING_CREATOR: "Your content is taking off! Keep up the great work!",
        BadgeType.PROVEN_PERFORMER: "You're now a Proven Performer! Your consistency is paying off!",
        BadgeType.TOP_CREATOR: "Congratulations! You're now among our Top Creators!",
        BadgeType.ELITE_PERFORMER: "Elite status achieved! You're in rarified air now!",
        BadgeType.CREATOR_LEGEND: "Legendary! You've become a Creator Legend!",
        BadgeType.HALL_OF_FAME: "Historic achievement! Welcome to the Hall of Fame!"
    },
    "progress": {
        "25": "You're 25% of the way to your next badge!",
        "50": "Halfway there! Keep pushing toward your next achievement!",
        "75": "Almost there! You're 75% of the way to your next badge!",
        "90": "So close! Just a little more to earn your next badge!"
    }
}


# Helper functions
def get_badge_by_type(badge_type: str) -> Optional[BadgeTier]:
    """Get badge tier by type"""
    return next((tier for tier in BADGE_TIERS if tier.badge_type == badge_type), None)


def get_badge_by_gmv(gmv: Decimal) -> Optional[BadgeTier]:
    """Get the highest badge tier for a given GMV"""
    eligible_badges = [
        tier for tier in BADGE_TIERS 
        if gmv >= tier.gmv_threshold
    ]
    return max(eligible_badges, key=lambda x: x.gmv_threshold) if eligible_badges else None


def get_next_badge(current_gmv: Decimal) -> Optional[BadgeTier]:
    """Get the next badge tier to achieve"""
    for tier in BADGE_TIERS:
        if current_gmv < tier.gmv_threshold:
            return tier
    return None


def calculate_badge_progress(current_gmv: Decimal, target_badge: BadgeTier) -> float:
    """Calculate progress percentage toward a badge"""
    if current_gmv >= target_badge.gmv_threshold:
        return 100.0
    return float((current_gmv / target_badge.gmv_threshold) * 100)