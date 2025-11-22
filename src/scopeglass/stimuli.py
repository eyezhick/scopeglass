"""Original English materials. Each lexical frame is one resampling unit."""

from dataclasses import asdict, dataclass
from itertools import product


@dataclass(frozen=True)
class Stimulus:
    id: str
    item: str
    experiment: str
    context: str
    target: str
    spillover: str
    factors: dict[str, str]

    def to_dict(self):
        return asdict(self)


# Singular, plural, relation, singular distractor, plural distractor, completion.
AGREEMENT = [
    ("key", "keys", "to", "cabinet", "cabinets", " on the table."),
    ("label", "labels", "on", "bottle", "bottles", " difficult to read."),
    ("picture", "pictures", "near", "window", "windows", " very old."),
    ("report", "reports", "about", "accident", "accidents", " on the desk."),
    ("ticket", "tickets", "for", "concert", "concerts", " expensive."),
    ("letter", "letters", "from", "teacher", "teachers", " in the drawer."),
    ("path", "paths", "around", "garden", "gardens", " muddy."),
    ("note", "notes", "about", "meeting", "meetings", " useful."),
    ("handle", "handles", "on", "door", "doors", " broken."),
    ("map", "maps", "of", "island", "islands", " inaccurate."),
    ("roof", "roofs", "above", "balcony", "balconies", " leaking."),
    ("sign", "signs", "beside", "road", "roads", " clearly visible."),
]

# Matrix subject, relative-clause subject, past-tense verb, matrix completion.
POLARITY = [
    ("senator", "journalist", "interviewed", " won an award."),
    ("author", "critic", "praised", " visited the museum."),
    ("actor", "director", "hired", " worked abroad."),
    ("scientist", "reporter", "contacted", " published a novel."),
    ("singer", "producer", "recommended", " performed in London."),
    ("teacher", "student", "thanked", " received a medal."),
    ("doctor", "patient", "trusted", " spoken on television."),
    ("lawyer", "witness", "recognized", " lost a case."),
    ("painter", "curator", "invited", " sold a sculpture."),
    ("chef", "customer", "complimented", " written a cookbook."),
    ("athlete", "coach", "selected", " competed overseas."),
    ("musician", "photographer", "noticed", " recorded an album."),
]


# Subject, optionally transitive verb, intransitive control, main subject,
# disambiguating main verb, spillover. NP/Z: noun-phrase object vs zero object.
GARDEN_PATH = [
    ("hunter", "hunted", "slept", "deer", "ran", " into the woods."),
    ("chef", "cooked", "sneezed", "soup", "cooled", " on the counter."),
    ("child", "ate", "laughed", "sandwich", "fell", " onto the floor."),
    ("student", "read", "yawned", "book", "slipped", " off the table."),
    ("woman", "painted", "danced", "wall", "crumbled", " in the heat."),
    ("boy", "washed", "slept", "dog", "barked", " at the door."),
    ("farmer", "milked", "coughed", "cow", "kicked", " the fence."),
    ("officer", "searched", "waited", "room", "filled", " with smoke."),
    ("driver", "parked", "hesitated", "truck", "rolled", " down the hill."),
    ("artist", "sketched", "smiled", "model", "sneezed", " very loudly."),
    ("sailor", "rowed", "shivered", "boat", "drifted", " toward the shore."),
    ("tailor", "sewed", "snored", "shirt", "tore", " at the seam."),
]


def generate(experiment="all") -> list[Stimulus]:
    if experiment not in {"all", "agreement", "polarity", "garden_path"}:
        raise ValueError(f"Unknown experiment: {experiment}")
    rows = []
    if experiment in {"all", "garden_path"}:
        for i, (subject, ambig, control, noun, verb, tail) in enumerate(GARDEN_PATH):
            item = f"npz-{i:02d}"
            for ambiguity, boundary in product(("ambiguous", "control"), ("absent", "comma")):
                subordinate = ambig if ambiguity == "ambiguous" else control
                comma = "," if boundary == "comma" else ""
                context = f"While the {subject} {subordinate}{comma} the {noun}"
                rows.append(Stimulus(
                    f"{item}-{ambiguity}-{boundary}", item, "garden_path", context,
                    f" {verb}", tail, {"ambiguity": ambiguity, "boundary": boundary},
                ))
    if experiment in {"all", "agreement"}:
        for i, (sg, pl, prep, dsg, dpl, tail) in enumerate(AGREEMENT):
            item = f"agr-{i:02d}"
            for head, distractor, verb in product(("sg", "pl"), repeat=3):
                context = (
                    f"The {sg if head == 'sg' else pl} {prep} the "
                    f"{dsg if distractor == 'sg' else dpl}"
                )
                rows.append(Stimulus(
                    f"{item}-{head}-{distractor}-{verb}", item, "agreement", context,
                    " is" if verb == "sg" else " are", tail,
                    {"head": head, "distractor": distractor, "verb": verb},
                ))
    if experiment in {"all", "polarity"}:
        for i, (head, embedded, verb, tail) in enumerate(POLARITY):
            item = f"npi-{i:02d}"
            for location, negation, target in product(
                ("matrix", "embedded"), ("absent", "present"), ("npi", "control")
            ):
                matrix_det = "No" if (location, negation) == ("matrix", "present") else "The"
                embedded_det = "no" if (location, negation) == ("embedded", "present") else "the"
                context = f"{matrix_det} {head} that {embedded_det} {embedded} {verb} has"
                rows.append(Stimulus(
                    f"{item}-{location}-{negation}-{target}", item, "polarity", context,
                    " ever" if target == "npi" else " often", tail,
                    {"location": location, "negation": negation, "target": target},
                ))
    return rows
