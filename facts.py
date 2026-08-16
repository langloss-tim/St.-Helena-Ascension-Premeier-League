"""A rotating 'fact of the day' about soccer. Picked deterministically from the
day of the year so it changes daily but is stable within a day."""

FACTS = [
    "Soccer is the most popular sport on Earth, followed by an estimated 3.5 billion fans.",
    "The fastest goal ever recorded was scored in about 2.4 seconds, straight from kick-off.",
    "A regulation match is 90 minutes, split into two 45-minute halves plus stoppage time.",
    "The World Cup is watched by more people than any other sporting event on the planet.",
    "Goalkeepers are the only players allowed to use their hands — and only inside their own box.",
    "A red card means a player is sent off, and their team must play the rest of the match a player down.",
    "The offside rule keeps attackers from camping next to the opponent's goal.",
    "A hat-trick is when one player scores three goals in a single match.",
    "The penalty spot sits 12 yards (11 metres) from the goal line.",
    "A standard soccer ball is a 'size 5' for players aged 12 and up.",
    "The pitch can be up to 120 yards long — bigger than an American football field.",
    "A clean sheet means a team finished a match without conceding any goals.",
    "The 'nutmeg' is when a player passes the ball between an opponent's legs.",
    "Throw-ins must be taken with both hands and both feet on the ground.",
    "The referee can add 'stoppage time' to make up for pauses during the half.",
    "A brace is when a single player scores two goals in one game.",
    "Corner kicks are awarded when the defending team last touches a ball that goes out over their own goal line.",
    "The captain wears an armband and helps lead the team on the pitch.",
    "A free kick is awarded to the team that was fouled.",
    "Yellow cards are warnings — two yellows in one match equal a red.",
    "Extra time is two 15-minute halves used to break a tie in knockout matches.",
    "A penalty shootout can decide a match when the score is still level after extra time.",
    "The 'derby' is a match between two rival clubs from the same area.",
    "Assists are credited to the player whose pass sets up a goal.",
    "The halfway line divides the pitch, and kick-off happens from its centre spot.",
    "Substitutions let fresh players come on to replace tired or injured teammates.",
    "A 'wall' of defenders lines up to block a dangerous free kick.",
    "The goalkeeper usually wears a different colour so the referee can tell them apart.",
    "A tackle is a fair attempt to win the ball from an opponent.",
    "'Added time' shown on the fourth official's board is the minimum that will be played.",
    "Every outfield player can be a scorer — even defenders on set pieces.",
    "The centre circle has a 10-yard radius that opponents must respect at kick-off.",
    "A 'volley' is a shot taken before the ball touches the ground.",
    "Home advantage is real: teams tend to win more often at their own stadium.",
    "A 'header' is scoring or passing the ball using your head.",
    "Goal difference — goals scored minus goals conceded — often breaks ties in the table.",
    "Three points are awarded for a win, one for a draw, and none for a loss.",
    "The 'golden generation' describes an unusually talented group of players in one era.",
    "Pressing is when a team hunts the ball aggressively to win it back quickly.",
    "A 'screamer' is a spectacular long-range goal.",
]


def fact_for_day(day_of_year):
    """Return the fact for a given 1-365 day-of-year (wraps safely)."""
    return FACTS[(day_of_year - 1) % len(FACTS)]
