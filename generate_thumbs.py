#!/usr/bin/env python3
"""Generate watercolor thumbnails for cats with no usable real photo, using
fal.ai FLUX.1 [schnell]. Appearances were researched from each cat's Wikipedia
article and web sources so the illustrations are as accurate as the record
allows. Reads FAL_KEY from .env. Writes img/<slug>.jpg and marks each cat
with "ai": true in cats_data.json (the page badges these as illustrations).

Run:  python3.11 generate_thumbs.py
"""
import json, os, re, io, time, pathlib
import requests
from PIL import Image

# --- load key from .env (KEY=VALUE), never printed ---
env = {}
for line in pathlib.Path(".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("FAL_KEY") or os.environ.get("FAL_KEY")
assert KEY, "FAL_KEY not found in .env"

ENDPOINT = "https://fal.run/fal-ai/flux/schnell"
STYLE = ("soft watercolor painting, loose washes on textured cream paper, "
         "naturalistic, gentle, subtle paint splatter, centered, isolated on "
         "pale parchment background, no text, no border, no words")

# Researched appearance per cat (see web search + Wikipedia). Portrait unless noted.
APPEARANCE = {
    "Homer the Blind Wonder Cat": "a small solid black short-haired cat with no eyes, eyelids gently closed, peaceful face",
    "Oscar (therapy cat)": "a medium-haired cat with a grey-and-brown back and white belly, sweet face",
    "Lewis (cat)": "a long-haired black-and-white cat with an alert, intense stare",
    "Michi (cat)": "a grey tabby-and-white cat wearing a small striped necktie and white collar",
    "Munich Mouser": "a sleek black cat sitting on a doorstep",
    "Room 8": "a thin grey-striped tabby cat with a chubby face, a white patch from chin down the chest, and a small notch in one ear",
    "Longjiaosun": "a friendly orange tabby cat wearing a small railway station-master cap",
    "Maru (cat)": "a plump brown-tabby-and-white Scottish Fold cat with a round face and normal upright ears",
    "Beerbohm (cat)": "a brown tabby cat lounging by theatre curtains",
    "Wilberforce (cat)": "a large black-and-white cat",
    "Pot Roast (cat)": "a fluffy black-and-white cat with a deadpan, sleepy, stiff expression",
    "Frank and Louie": "a fluffy seal-point Ragdoll cat with vivid blue eyes",
    "Simpkin (cat)": "a black-and-white cat",
    "Catmando": "a ginger-and-white tabby cat",
    "Stewie (cat)": "an enormous long grey-tabby Maine Coon cat, long flowing fur, majestic",
    "Dorofei": "a fluffy Siberian Neva-Masquerade cat with grey-blue points and blue eyes",
    "PepitoTheCat": "a black-and-white cat stepping through a cat flap at night",
    "Billi (cat)": "a grey domestic shorthair tabby cat",
    "Flossie (cat)": "a very old tortoiseshell cat with mottled brown-and-black fur",
    "Elsie (cat)": "a calico cat, white with orange and black patches, bright eyes",
    "Prince Chunk": "a very large, overweight grey-and-white tabby domestic shorthair cat",
    "Little Nicky (cat)": "a brown tabby Maine Coon cat",
    "Peter (chief mouser)": "a sleek black cat",
    "Colonel Meow": "a grumpy long-haired grey-and-white Himalayan-Persian cat with extremely long fur and a flat face",
    "Creme Puff (cat)": "a brown tabby cat, elderly and content",
    "Luna the Fashion Kitty": "a cream Himalayan cat with darker points, fluffy, flat face",
    "Venus (cat)": "a chimera cat whose face is split vertically down the middle, one half solid black and the other half orange tabby, with heterochromia: one blue eye and one green eye",
    "Lord Tubbington": "a chubby spotted brown Bengal cat",
    "Rusik": "a Siamese cat, cream body with dark-brown points and blue eyes",
    "Peter (Lord's cat)": "a sleek black cat on a green cricket field",
    "Chico (cat)": "a brown tabby cat",
    "Rufus of England": "a ginger tabby cat",
    "Olivia Benson (cat)": "a grey-and-white Scottish Fold cat with folded ears",
    "Tara (cat)": "a short-haired brown tabby cat with a brave, protective expression",
    "Dusty the Klepto Kitty": "a Siamese-mix cat carrying a small item in its mouth",
    "F. D. C. Willard": "a Siamese cat",
    "Stepan (cat)": "a grey striped tabby cat",
    "Jones (fictional cat)": "a ginger orange cat aboard a spaceship, slightly wary",
    "Choupette": "a fluffy cream-white Birman cat with striking blue eyes",
    "Tuxedo Stan": "a black-and-white tuxedo cat",
    # special (scene, not a portrait): cryptid puma sighting
    "Winnie (feline)": "__WINNIE__",
}
SKIP = {"Eros (cat)", "Polleke (cat)", "Musashi's"}  # can't depict honestly


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def generate(prompt):
    r = requests.post(ENDPOINT, headers={"Authorization": f"Key {KEY}"},
                      json={"prompt": prompt, "image_size": "square",
                            "num_images": 1, "num_inference_steps": 4,
                            "enable_safety_checker": True}, timeout=120)
    r.raise_for_status()
    url = r.json()["images"][0]["url"]
    img = requests.get(url, timeout=60).content
    return Image.open(io.BytesIO(img)).convert("RGB")


def main():
    gen = json.load(open("/tmp/gen_list.json"))
    data = json.load(open("cats_data.json"))
    by_name = {c["name"]: c for c in data["cats"]}
    pathlib.Path("img").mkdir(exist_ok=True)

    done = 0
    for name in gen:
        if name in SKIP:
            print(f"  skip (cannot depict honestly): {name}"); continue
        if name not in APPEARANCE:
            print(f"  WARN no prompt for: {name}"); continue
        app = APPEARANCE[name]
        if app == "__WINNIE__":
            prompt = ("watercolor painting of a wild puma (cougar) half-hidden in "
                      "a misty Dutch pine forest at dusk, atmospheric, " + STYLE)
        else:
            prompt = f"watercolor portrait of {app}, head and shoulders, facing the viewer, {STYLE}"
        try:
            im = generate(prompt)
            im.thumbnail((256, 256))
            path = f"img/{slug(name)}.jpg"
            im.save(path, "JPEG", quality=88, optimize=True)
            by_name[name]["thumb"] = path
            by_name[name]["ai"] = True
            done += 1
            print(f"  [{done}] {name} -> {path}")
        except Exception as e:
            print(f"  FAIL {name}: {e}")
        time.sleep(0.3)

    json.dump(data, open("cats_data.json", "w"), ensure_ascii=False, indent=1)
    print(f"\nGenerated {done} thumbnails. Skipped {len(SKIP)} "
          f"({', '.join(sorted(SKIP))}).")
    missing = [c['name'] for c in data['cats'] if not c['thumb']]
    print(f"Still without any image: {len(missing)} -> {missing}")


if __name__ == "__main__":
    main()
