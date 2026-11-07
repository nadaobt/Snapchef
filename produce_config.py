
COLOR_BINS = ["red", "orange", "yellow", "green", "brown", "white", "dark", "purple", "other"]

PRODUCE = {
    "Tomato": {
        "no": "Tomat",
        "prompts": ["a photo of a ripe red tomato", "a photo of fresh tomatoes on a vine"],
        "colors": [{"red": 0.85, "orange": 0.07, "green": 0.08}],
        "aspect": (0.8, 1.5),
    },
    "Cucumber": {
        "no": "Agurk",
        "prompts": [
            "a photo of a fresh green cucumber with smooth or bumpy shiny skin", 
            "a long green cucumber on a table",
            "a whole European cucumber"
        ],
        "colors": [{"green": 0.85, "dark": 0.07, "yellow": 0.04, "white": 0.04}],
        "aspect": (1.8, 8.0),
    },
    "Carrot": {
        "no": "Gulrot",
        "prompts": ["a photo of an orange carrot", "a photo of fresh carrots"],
        "colors": [{"orange": 0.8, "red": 0.08, "brown": 0.05, "green": 0.07}],
        "aspect": (2.2, 10.0),
    },
    "Bell pepper": {
        "no": "Paprika",
        "prompts": [
            "a photo of a red bell pepper",
            "a photo of a yellow bell pepper",
            "a photo of a green bell pepper",
            "a photo of an orange bell pepper"
        ],
        "colors": [
            {"red": 0.9, "orange": 0.1},
            {"green": 0.9, "dark": 0.1},
            {"yellow": 0.85, "orange": 0.15},
            {"orange": 0.9, "yellow": 0.1}
        ],
        "aspect": (0.9, 1.6),
    },
    "Broccoli": {
        "no": "Brokkoli",
        "prompts": ["a photo of fresh green broccoli", "a photo of a head of broccoli"],
        "colors": [{"green": 0.85, "dark": 0.1, "white": 0.05}],
        "aspect": (0.8, 1.8),
    },
    "Cauliflower": {
        "no": "Blomkål",
        "prompts": ["a photo of white cauliflower", "a photo of a head of cauliflower"],
        "colors": [{"white": 0.7, "yellow": 0.15, "green": 0.1, "brown": 0.05}],
        "aspect": (0.8, 1.6),
    },
    "Potato": {
        "no": "Potet",
        "prompts": ["a photo of brown potatoes", "a photo of raw potatoes"],
        "colors": [{"brown": 0.7, "yellow": 0.15, "orange": 0.1, "dark": 0.05}],
        "aspect": (1.0, 2.0),
    },
    "Onion": {
        "no": "Løk",
        "prompts": ["a photo of a yellow onion", "a photo of a red onion"],
        "colors": [
            {"brown": 0.5, "yellow": 0.3, "orange": 0.2},
            {"purple": 0.5, "red": 0.3, "white": 0.2}
        ],
        "aspect": (0.8, 1.5),
    },
    "Zucchini": {
        "no": "Squash",
        "prompts": [
            "a photo of a green zucchini courgette with a small stem at the end", 
            "a dark green squash vegetable",
            "a fresh zucchini with matte skin and slight ridges"
        ],
        "colors": [{"green": 0.8, "dark": 0.15, "yellow": 0.05}],
        "aspect": (1.8, 6.0),
    },
    "Mushroom": {
        "no": "Sopp",
        "prompts": ["a photo of white button mushrooms", "a photo of fresh mushrooms"],
        "colors": [{"white": 0.6, "brown": 0.3, "dark": 0.1}],
        "aspect": (0.8, 1.7),
    },
    "Lettuce": {
        "no": "Salat",
        "prompts": [
            "a photo of fresh green lettuce leaves",
            "a photo of romaine lettuce",
            "a photo of iceberg lettuce"
        ],
        "colors": [{"green": 0.75, "white": 0.15, "yellow": 0.05, "dark": 0.05}],
        "aspect": (0.8, 2.5),
    },
    "Corn": {
        "no": "Mais",
        "prompts": [
            "a photo of corn on the cob",
            "a photo of fresh corn with husk",
            "a photo of yellow corn"
        ],
        "colors": [{"yellow": 0.6, "green": 0.3, "white": 0.05, "brown": 0.05}],
        "aspect": (2.0, 5.0),
    },
    "Garlic": {
        "no": "Hvitløk",
        "prompts": [
            "a photo of a garlic bulb",
            "a photo of white garlic",
            "a photo of garlic cloves"
        ],
        "colors": [{"white": 0.7, "yellow": 0.15, "brown": 0.1, "other": 0.05}],
        "aspect": (0.8, 1.3),
    },
    "Eggplant": {
        "no": "Aubergine",
        "prompts": ["a photo of a purple eggplant", "a photo of an aubergine"],
        "colors": [{"purple": 0.7, "dark": 0.2, "green": 0.1}],
        "aspect": (1.5, 4.0),
    },
    "Avocado": {
        "no": "Avokado",
        "prompts": ["a photo of a green avocado", "a photo of a ripe avocado"],
        "colors": [{"green": 0.6, "dark": 0.3, "brown": 0.1}],
        "aspect": (1.2, 2.0),
    },
        "Ginger": {
        "no": "Ingefær",
        "prompts": ["a photo of fresh ginger root", "a photo of a piece of raw ginger"],
        "colors": [{"brown": 0.5, "yellow": 0.3, "orange": 0.2}],
        "aspect": (1.0, 3.0),
    },
    "Spinach": {
        "no": "Spinat",
        "prompts": ["a photo of fresh spinach leaves", "a photo of green spinach"],
        "colors": [{"green": 0.8, "dark": 0.15, "other": 0.05}],
        "aspect": (0.5, 2.0),
    },
    "Kale": {
        "no": "Grønnkål",
        "prompts": ["a photo of kale leaves", "a photo of fresh green kale"],
        "colors": [{"green": 0.75, "dark": 0.2, "purple": 0.05}],
        "aspect": (0.5, 2.0),
    },
    "Cabbage": {
        "no": "Kål",
        "prompts": ["a photo of a head of cabbage", "a photo of green cabbage"],
        "colors": [{"green": 0.7, "white": 0.2, "yellow": 0.1}],
        "aspect": (0.8, 1.5),
    },
    "Peas": {
        "no": "Erter",
        "prompts": ["a photo of green peas", "a photo of fresh peas in pod"],
        "colors": [{"green": 0.8, "yellow": 0.15, "white": 0.05}],
        "aspect": (1.0, 3.0),
    },
    "Asparagus": {
        "no": "Asparges",
        "prompts": ["a photo of green asparagus", "a photo of fresh asparagus spears"],
        "colors": [{"green": 0.75, "white": 0.15, "yellow": 0.1}],
        "aspect": (3.0, 12.0),
    },
    "Pumpkin": {
        "no": "Gresskar",
        "prompts": ["a photo of an orange pumpkin", "a photo of a pumpkin"],
        "colors": [{"orange": 0.8, "yellow": 0.15, "green": 0.05}],
        "aspect": (0.8, 1.5),
    },
    "Fennel": {
        "no": "Fennikel",
        "prompts": ["a photo of fresh fennel", "a photo of fennel bulb"],
        "colors": [{"white": 0.6, "green": 0.3, "yellow": 0.1}],
        "aspect": (0.8, 2.0),
    },
    "Radish": {
        "no": "Reddik",
        "prompts": ["a photo of red radishes", "a photo of fresh radishes"],
        "colors": [{"red": 0.7, "white": 0.2, "green": 0.1}],
        "aspect": (0.8, 1.5),
    },
    "Beet": {
        "no": "Rødbete",
        "prompts": ["a photo of red beets", "a photo of fresh beets"],
        "colors": [{"purple": 0.6, "red": 0.3, "dark": 0.1}],
        "aspect": (0.8, 1.5),
    },
    "Celery": {
        "no": "Selleri",
        "prompts": ["a photo of celery stalks", "a photo of fresh green celery"],
        "colors": [{"green": 0.8, "yellow": 0.15, "white": 0.05}],
        "aspect": (2.0, 8.0),
    },
        "Parsley": {
        "no": "Persille",
        "prompts": ["a photo of fresh parsley", "a bunch of green parsley leaves"],
        "colors": [{"green": 0.85, "dark": 0.1, "yellow": 0.05}],
        "aspect": (0.6, 2.5),
    },
    "Leek": {
        "no": "Purreløk",
        "prompts": ["a photo of fresh leeks", "a photo of green and white leek"],
        "colors": [{"green": 0.5, "white": 0.4, "yellow": 0.1}],
        "aspect": (2.0, 6.0),
    },
    
    # ========== FRUKT ==========
    "Apple": {
        "no": "Eple",
        "prompts": ["a photo of red apples", "a photo of a red apple", "a photo of fresh apples on a table"],
        "colors": [{"red": 0.7, "green": 0.2, "yellow": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Pear": {
        "no": "Pære",
        "prompts": ["a photo of a pear", "a photo of fresh pears"],
        "colors": [{"yellow": 0.6, "green": 0.3, "brown": 0.1}],
        "aspect": (1.0, 1.8),
    },
    "Banana": {
        "no": "Banan",
        "prompts": ["a photo of yellow bananas", "a photo of fresh bananas"],
        "colors": [{"yellow": 0.85, "green": 0.1, "brown": 0.05}],
        "aspect": (2.0, 6.0),
    },
    "Orange": {
        "no": "Appelsin",
        "prompts": ["a photo of oranges", "a photo of fresh oranges"],
        "colors": [{"orange": 0.9, "yellow": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Lemon": {
        "no": "Sitron",
        "prompts": ["a photo of lemons", "a photo of fresh yellow lemons"],
        "colors": [{"yellow": 0.9, "green": 0.1}],
        "aspect": (0.8, 1.5),
    },
    "Lime": {
        "no": "Lime",
        "prompts": ["a photo of limes", "a photo of fresh green limes"],
        "colors": [{"green": 0.9, "yellow": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Grapefruit": {
        "no": "Grapefrukt",
        "prompts": ["a photo of grapefruit", "a photo of fresh grapefruits"],
        "colors": [{"orange": 0.6, "yellow": 0.3, "pink": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Grapes": {
        "no": "Druer",
        "prompts": ["a photo of grapes", "a photo of fresh grapes on a vine"],
        "colors": [{"purple": 0.5, "green": 0.3, "red": 0.2}],
        "aspect": (0.8, 2.0),
    },
    "Strawberry": {
        "no": "Jordbær",
        "prompts": ["a photo of fresh strawberries", "a photo of red strawberries"],
        "colors": [{"red": 0.8, "green": 0.15, "white": 0.05}],
        "aspect": (0.8, 1.5),
    },
    "Blueberry": {
        "no": "Blåbær",
        "prompts": ["a photo of blueberries", "a photo of fresh blueberries"],
        "colors": [{"blue": 0.6, "purple": 0.3, "dark": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Raspberry": {
        "no": "Bringebær",
        "prompts": ["a photo of raspberries", "a photo of fresh raspberries"],
        "colors": [{"red": 0.8, "purple": 0.15, "other": 0.05}],
        "aspect": (0.8, 1.3),
    },
    "Blackberry": {
        "no": "Bjørnebær",
        "prompts": ["a photo of blackberries", "a photo of fresh blackberries"],
        "colors": [{"dark": 0.6, "purple": 0.3, "red": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Cherry": {
        "no": "Kirsebær",
        "prompts": ["a photo of cherries", "a photo of fresh red cherries"],
        "colors": [{"red": 0.8, "dark": 0.15, "green": 0.05}],
        "aspect": (0.8, 1.3),
    },
    "Peach": {
        "no": "Fersken",
        "prompts": ["a photo of peaches", "a photo of fresh peaches"],
        "colors": [{"orange": 0.5, "yellow": 0.3, "red": 0.2}],
        "aspect": (0.8, 1.3),
    },
    "Nectarine": {
        "no": "Nektarin",
        "prompts": ["a photo of nectarines", "a photo of fresh nectarines"],
        "colors": [{"orange": 0.5, "yellow": 0.3, "red": 0.2}],
        "aspect": (0.8, 1.3),
    },
    "Plum": {
        "no": "Plomme",
        "prompts": ["a photo of plums", "a photo of fresh plums"],
        "colors": [{"purple": 0.6, "red": 0.3, "yellow": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Mango": {
        "no": "Mango",
        "prompts": ["a photo of mango", "a photo of fresh mangoes"],
        "colors": [{"orange": 0.5, "yellow": 0.3, "green": 0.2}],
        "aspect": (1.0, 2.0),
    },
    "Pineapple": {
        "no": "Ananas",
        "prompts": ["a photo of pineapple", "a photo of fresh pineapple"],
        "colors": [{"yellow": 0.5, "brown": 0.3, "green": 0.2}],
        "aspect": (1.5, 3.0),
    },
    "Kiwi": {
        "no": "Kiwi",
        "prompts": ["a photo of kiwi fruit", "a photo of fresh kiwis"],
        "colors": [{"brown": 0.6, "green": 0.3, "yellow": 0.1}],
        "aspect": (0.8, 1.3),
    },
    "Watermelon": {
        "no": "Vannmelon",
        "prompts": ["a photo of watermelon", "a photo of fresh watermelon"],
        "colors": [{"green": 0.6, "red": 0.3, "dark": 0.1}],
        "aspect": (1.0, 2.0),
    },
    "Melon": {
        "no": "Honningmelon",
        "prompts": ["a photo of cantaloupe melon", "a photo of fresh melon"],
        "colors": [{"orange": 0.5, "yellow": 0.3, "green": 0.2}],
        "aspect": (0.8, 1.5),
    },
    "Pomegranate": {
        "no": "Granateple",
        "prompts": ["a photo of pomegranate", "a photo of fresh pomegranate"],
        "colors": [{"red": 0.7, "purple": 0.2, "dark": 0.1}],
        "aspect": (0.8, 1.3),
    },
}

UNKNOWN_LABEL = "unknown"
NEGATIVE_PROMPTS = [
    "a photo of packaged food",
    "a photo of a person",
    "a photo of an empty table",
    "a photo of meat or fish",
    "a photo of a beverage",
    "a photo of bread",
]