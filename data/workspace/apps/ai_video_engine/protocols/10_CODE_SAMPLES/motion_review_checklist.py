REVIEW_ITEMS = [
    "weight shift feels natural",
    "feet contact looks grounded",
    "arms do not snap or bend unnaturally",
    "head motion matches body momentum",
    "timing contains anticipation and follow-through",
]

def print_checklist():
    for i, item in enumerate(REVIEW_ITEMS, 1):
        print(f"{i}. {item}")

if __name__ == "__main__":
    print_checklist()
