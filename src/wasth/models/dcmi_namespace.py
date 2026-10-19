from typing import Literal

TITLE_TYPE = Literal[
    "brandName",
    "cited",
    "creator",
	"descriptive",
	"former",
	"inscribed",
	"owner",
	"popular",
	"repository",
	"translated",
	"other"
]

ACTOR_TYPE = Literal[
    'personal',
	'corporate',
	'family',
	'other'
]

REPO_TYPE = Literal[
    'corporate',
    'geographic',
    'personal',
    'other'
]

