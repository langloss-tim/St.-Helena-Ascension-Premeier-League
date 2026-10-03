"""Two rotating 'fact of the day' feeds — one about soccer, one about Curaçao. Each is picked deterministically from the day of the year, using a
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

CURACAO_FACTS = [
    "Curaçao became its own country within the Kingdom of the Netherlands on 10 October 2010, when the Netherlands Antilles were dissolved.",
    "The historic centre of Willemstad and its harbour have been a UNESCO World Heritage Site since 1997.",
    "The Queen Emma Bridge in Willemstad is a floating pontoon bridge that swings aside to let ships into the harbour. It first opened in 1888.",
    "The Queen Juliana Bridge stands about 185 feet above the water, one of the highest bridges in the Caribbean.",
    "Most people on Curaçao speak Papiamentu. It is an official language alongside Dutch and English.",
    "The Mikvé Israel-Emanuel synagogue in Willemstad, consecrated in 1732, is the oldest synagogue in continuous use in the Americas, and its floor is covered in sand.",
    "Blue Curaçao liqueur is flavoured with the dried peel of the laraha, a bitter orange that grows on the island.",
    "Landhuis Chobolobo, an old plantation house in Willemstad, is where the original Curaçao liqueur is still made.",
    "Curaçao lies about 40 miles off the coast of Venezuela.",
    "Curaçao is the C in the ABC islands, alongside Aruba and Bonaire.",
    "The highest point on Curaçao is Christoffelberg, about 1,220 feet high, inside Christoffel National Park.",
    "Curaçao sits south of the main hurricane belt, so big hurricanes rarely hit the island.",
    "The two white stars on Curaçao's flag stand for Curaçao and the small uninhabited island of Klein Curaçao.",
    "Flag Day in Curaçao is 2 July, the date the flag was adopted in 1984.",
    "Curaçao qualified for the 2026 FIFA World Cup and became the smallest country by population ever to reach the tournament.",
    "In 2025 Curaçao and Sint Maarten swapped the Netherlands Antillean guilder for a new currency, the Caribbean guilder.",
    "Flamingos feed in the salt pans at Jan Kok on the west side of the island.",
    "Willemstad is split by the Sint Anna Bay into Punda and Otrobanda, which means 'the other side'.",
    "Local legend says the waterfront houses of Punda were painted bright colours because a governor got headaches from the glare off white walls.",
    "Major League Baseball stars Andruw Jones, Kenley Jansen, Ozzie Albies and Jurickson Profar all grew up on Curaçao.",
    "A team from Willemstad won the Little League World Series in 2004.",
    "On 17 August 1795 an enslaved man named Tula led a major uprising on Curaçao. The day is now remembered every year.",
    "The Dutch West India Company took Curaçao from Spain in 1634.",
    "The Hato Caves are limestone caves with rock drawings made by the island's early Indigenous people.",
    "Shete Boka National Park, whose name means 'seven inlets', is known for waves crashing into the coastal rock.",
    "Keshi yena, a ball of cheese stuffed with spiced meat, is one of Curaçao's best-known dishes.",
    "Tumba is Curaçao's traditional music, and a tumba contest picks the official road march for Carnival.",
    "Seú is Curaçao's harvest festival, celebrated with music and dancing every Easter Monday.",
    "Curaçao covers about 171 square miles and is home to roughly 155,000 people.",
    "The Curaçao North Sea Jazz Festival has been held in Willemstad nearly every year since 2010.",
]


# Pinned Curaçao fact. While this is set it is what the card shows EVERY day,
# instead of rotating. Set it back to None to return to the daily rotation.
PINNED_CURACAO_FACT = None


def _pick(items, day_of_year, offset=0):
    return items[(day_of_year - 1 + offset) % len(items)]


def soccer_fact(day_of_year):
    return _pick(SOCCER_FACTS, day_of_year)


def curacao_fact(day_of_year):
    if PINNED_CURACAO_FACT:
        return PINNED_CURACAO_FACT
    # different offset so the two feeds don't move in lockstep
    return _pick(CURACAO_FACTS, day_of_year, offset=7)


# Backwards-compatible alias
def fact_for_day(day_of_year):
    return soccer_fact(day_of_year)
