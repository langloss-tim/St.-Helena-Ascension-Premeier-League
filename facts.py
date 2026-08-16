"""Two rotating 'fact of the day' feeds — one about soccer, one about St. Helena
& Ascension. Each is picked deterministically from the day of the year, using a
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

STHELENA_FACTS = [
    "St. Helena is one of the most remote inhabited places on Earth — roughly 1,900 km from the nearest mainland, Africa.",
    "Napoleon Bonaparte was exiled to St. Helena in 1815 and died there in 1821, at Longwood House.",
    "Jonathan, a giant tortoise living on St. Helena, is the oldest known land animal alive — hatched around 1832.",
    "Until the airport opened in 2016, the only way to reach St. Helena was a multi-day voyage on the RMS St Helena mail ship.",
    "Jacob's Ladder, a staircase in the capital Jamestown, climbs 699 steep steps up the valley wall.",
    "The St Helena plover, known locally as the 'wirebird', is the island's national bird and lives nowhere else on Earth.",
    "Ascension Island, about 1,300 km northwest of St. Helena, is one of the world's most important green turtle nesting sites.",
    "Charles Darwin visited both islands aboard HMS Beagle in 1836.",
    "Ascension's Green Mountain has a man-made cloud forest, deliberately planted in the 1800s with Darwin's involvement.",
    "St. Helena, Ascension and Tristan da Cunha together form a single British Overseas Territory.",
    "St. Helena's capital, Jamestown, is squeezed into a narrow, steep-sided volcanic valley.",
    "Ascension Island has no native population — everyone there lives and works on assignment.",
    "The waters around St. Helena are a global hotspot for whale sharks, the largest fish in the sea.",
    "Both islands are the tips of huge volcanoes rising from the floor of the South Atlantic.",
    "The islands use the St Helena pound, which is kept equal in value to the British pound.",
    "St. Helena's whole population is only around 4,400 people — smaller than many football crowds.",
    "Two Boats and Georgetown are two of the small settlements on Ascension Island.",
    "Ascension served as a vital Allied airbase in World War II and later hosted a NASA tracking station.",
    "St. Helena was uninhabited when the Portuguese discovered it in 1502 — humans only settled later.",
    "The island's flag features the wirebird, its unique and endangered native bird.",
    "Half Tree Hollow is one of the most populated districts on St. Helena, perched above Jamestown.",
    "Longwood, on St. Helena, takes its name from the estate where Napoleon spent his final years.",
    "St. Helena grows its own coffee, descended from seeds brought to the island in 1733 — it's prized worldwide.",
    "Ascension's beaches glow at night during turtle season as hatchlings scramble for the sea.",
    "The RMS St Helena was one of the last working ocean-going Royal Mail Ships in the world.",
    "St. Helena has its own time zone, Greenwich Mean Time, all year round.",
    "The island's rugged terrain means roads twist through dramatic hairpins and sheer drops.",
    "Ascension's 'Devil's Riding School' is a striking volcanic crater in a barren, Mars-like landscape.",
    "Endemic plants like the St Helena gumwood, the national tree, grow nowhere else on the planet.",
    "Because it's so isolated, St. Helena is a haven for rare wildlife found in no other place on Earth.",
]


def _pick(items, day_of_year, offset=0):
    return items[(day_of_year - 1 + offset) % len(items)]


def soccer_fact(day_of_year):
    return _pick(SOCCER_FACTS, day_of_year)


def sthelena_fact(day_of_year):
    # different offset so the two feeds don't move in lockstep
    return _pick(STHELENA_FACTS, day_of_year, offset=7)


# Backwards-compatible alias
def fact_for_day(day_of_year):
    return soccer_fact(day_of_year)
