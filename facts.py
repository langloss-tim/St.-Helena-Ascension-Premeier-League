"""Two rotating 'fact of the day' feeds — one about soccer, one about Barbados. Each is picked deterministically from the day of the year, using a
different offset so both change every day and don't line up with each other."""

SOCCER_FACTS = [
    "The highest score in a pro match was 149–0, in Madagascar in 2002 — the losing side scored every goal on purpose in protest.",
    "Sheffield FC, founded in 1857 in England, is recognised as the world's oldest football club.",
    "Brazil is the only nation to have played in every single World Cup since it began in 1930.",
    "The fastest red card ever came after about 2 seconds — a player swore at the referee straight from kick-off.",
    "The FIFA World Cup trophy is made of solid 18-carat gold and weighs over 6 kilograms.",
    "Denmark won Euro 1992 despite not qualifying — they were called up last-minute and some players came off holiday.",
    "The classic black-and-white ball has 32 panels: 20 hexagons and 12 pentagons.",
    "Cristiano Ronaldo has scored over 900 career goals, more than any other player in history.",
    "The 1950 World Cup final at the Maracanã drew a crowd estimated near 200,000 — a record that still stands.",
    "'Soccer' comes from 'association football', shortened from 'assoc' by British students.",
    "A goalkeeper can legally score — several have, including from their own box with a huge kick.",
    "Only eight different nations have ever won the men's World Cup.",
    "The longest official match on record lasted over 3 hours during a 1946 English cup replay.",
    "Referees didn't use whistles until the 1870s — before that they waved handkerchiefs.",
    "The Premier League is watched in over 200 countries and territories worldwide.",
    "Yellow and red cards were introduced at the 1970 World Cup, inspired by traffic lights.",
    "Lionel Messi has won the Ballon d'Or a record number of times.",
    "The very first World Cup, in 1930, was won by the host nation, Uruguay.",
    "A standard match ball must be inflated to a pressure set by the laws of the game — too soft or too hard is illegal.",
    "The 'bicycle kick' is named for the pedalling motion a player makes while airborne.",
    "Women's football drew crowds of over 50,000 in England a century ago — before it was banned there for decades.",
    "The word 'hat-trick' came from cricket, where a bowler earned a new hat for three wickets in a row.",
    "Goal-line technology can detect the ball crossing the line to within a few millimetres.",
    "The most-capped men's international player has appeared for his country over 200 times.",
    "AC Milan and Inter share the same stadium, the San Siro, and play a fierce city derby there.",
    "A match is officially over only when the referee blows the final whistle — not when the clock hits 90.",
    "Pelé is the only player to have won the World Cup three times, in 1958, 1962 and 1970.",
    "The 2022 World Cup final between Argentina and France is widely called one of the greatest ever.",
    "Some stadiums are so loud that crowd noise has literally registered on earthquake sensors.",
    "The offside rule has existed, in some form, since the very first written laws of football in 1863.",
]

BARBADOS_FACTS = [
    "Barbados became a republic on 30 November 2021, exactly 55 years after independence, with Dame Sandra Mason as its first president.",
    "Rihanna was born and raised in Barbados and was named a National Hero of the country in 2021.",
    "George Washington's only trip abroad was to Barbados in 1751 — the house he stayed in is now a museum.",
    "Mount Gay, with records dating back to 1703, is often called the oldest rum brand still in existence.",
    "The grapefruit first appeared in Barbados in the 1700s as a natural cross — early on it was called the 'forbidden fruit'.",
    "The flag's broken trident stands for Barbados breaking away from its colonial past.",
    "Barbados is the easternmost island of the Caribbean, sitting out in the Atlantic Ocean.",
    "Kensington Oval in Bridgetown hosted the Cricket World Cup final in 2007 and the T20 World Cup final in 2024.",
    "Bajan cricket great Sir Garfield Sobers hit six sixes in a single over in 1968 — the first player ever to do it.",
    "Crop Over began in the 1780s to celebrate the end of the sugar cane harvest and ends with Grand Kadooment Day.",
    "The national dish of Barbados is cou-cou and flying fish.",
    "Flying fish are so linked to Barbados that one is pictured on the island's coins.",
    "Harrison's Cave is a crystal-filled limestone cave that visitors tour by tram.",
    "Most of Barbados is made of coral limestone, which naturally filters the island's drinking water.",
    "The highest point in Barbados is Mount Hillaby, at about 1,100 feet.",
    "People from Barbados are called Bajans.",
    "Barbados covers about 166 square miles — smaller than New York City.",
    "The Barbados House of Assembly first met in 1639, making it one of the oldest parliaments in the Americas.",
    "Barbados won independence from Britain on 30 November 1966, with Errol Barrow as its first Prime Minister.",
    "A British Airways Concorde is kept on display at Grantley Adams International Airport.",
    "Speightstown, the second-largest town, was nicknamed 'Little Bristol' for its old trade with Bristol, England.",
    "Barbados' green monkeys are descended from monkeys brought over from West Africa in the 1600s.",
    "The Barbados national football team is nicknamed the Bajan Tridents.",
    "Hawksbill and leatherback turtles nest on the beaches of Barbados.",
    "Traditional Bajan chattel houses were built of wood so workers could take their homes apart and move them.",
    "The Barbados dollar has been fixed at two to one US dollar since 1975.",
    "Mia Mottley became the first woman Prime Minister of Barbados in 2018.",
    "Historic Bridgetown and its Garrison were named a UNESCO World Heritage Site in 2011.",
    "The 'Soup Bowl' at Bathsheba, on the rugged Atlantic coast, is one of the Caribbean's best-known surf spots.",
    "The national flower of Barbados is the Pride of Barbados, a bright red and yellow bloom.",
]


# Pinned Barbados fact. While this is set it is what the card shows EVERY day,
# instead of rotating. Set it back to None to return to the daily rotation.
PINNED_BARBADOS_FACT = None


def _pick(items, day_of_year, offset=0):
    return items[(day_of_year - 1 + offset) % len(items)]


def soccer_fact(day_of_year):
    return _pick(SOCCER_FACTS, day_of_year)


def barbados_fact(day_of_year):
    if PINNED_BARBADOS_FACT:
        return PINNED_BARBADOS_FACT
    # different offset so the two feeds don't move in lockstep
    return _pick(BARBADOS_FACTS, day_of_year, offset=7)


# Backwards-compatible alias
def fact_for_day(day_of_year):
    return soccer_fact(day_of_year)
