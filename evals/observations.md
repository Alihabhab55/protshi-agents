# Observations — week 2

First look at what the extractor gets right and what it makes up.
Model `claude-opus-5`, effort `low`, nine-field system prompt + JSON schema
(`describe_one.py` as of W02·D5). Raw replies are in `evals/raw/`.

**Verdict key**
- ✅ **right**: visible in the photo and correct
- ⚠️ **guess**: plausible, but the photo can't prove it
- ❌ **invented**: stated as fact with nothing in the photo to support it, or wrong
- 🔍 **missed**: visible in the photo, not mentioned

Material is marked ⚠️ everywhere: a photo can't tell real leather from faux.
**Confirm the real material for each bag from the supplier/product info.**

---

## 1. IMG_2417 — black quilted mini tote

| Field | Value | Verdict |
|---|---|---|
| title | Braided Quilt Leather Mini Tote | ✅ |
| product_type | tote | ✅ |
| colour | black | ✅ |
| material | quilted leather | ⚠️ real vs faux unknown |
| size | small | ❌ contradicts its own title ("Mini") |
| closure | zip | ✅ zip pull visible top right |
| description | chevron quilting, knotted handles, silver eyelets, front patch | ✅ all visible |
| seo_description | | ✅ |
| tags | tote, black, leather, quilted, zip, small bag, handbag | ✅ |

Note: three runs on this photo gave three different titles ("Quilted Chevron Mini
Tote", "Chevron Quilted Leather Mini Tote", "Braided Quilt Leather Mini Tote").
Same photo, same prompt, different wording each time.

## 2. IMG_2429 — taupe pebbled tote

| Field | Value | Verdict |
|---|---|---|
| title | Taupe Pebbled Structured Day Tote | ✅ |
| product_type | tote | ✅ |
| colour | taupe | ✅ |
| material | pebbled faux leather | ⚠️ pebbled texture ✅, "faux" is a guess |
| size | medium | ⚠️ nothing in the photo for scale |
| closure | not visible | ✅ correctly admitted it can't see |
| description | twin rolled handles, gold side rings | ✅ / ❌ "allow for an extra shoulder strap" — no strap shown |
| seo_description | "for work and weekends" | ⚠️ marketing filler, harmless |
| tags | includes "work bag" | ⚠️ opinion, not visible |

## 3. IMG_2431 — taupe panelled tote

| Field | Value | Verdict |
|---|---|---|
| title | Taupe Panelled Structured Tote | ✅ |
| product_type | tote | ✅ |
| colour | taupe | ✅ |
| material | faux leather | ⚠️ |
| size | medium | ⚠️ |
| closure | not visible | ✅ |
| description | smooth centre + pebbled side panels, gold hardware, side rings | ✅ best description of the five |
| seo_description | | ✅ |
| tags | includes "work bag", "neutral" | ⚠️ opinion |

🔍 Missed: the handle anchors are long gold oval loops, a distinctive detail; it only says
"gold-tone hardware".

## 4. IMG_2433 — tan pebbled tote

| Field | Value | Verdict |
|---|---|---|
| title | Tan Pebbled Structured Tote Handbag | ✅ |
| product_type | tote | ✅ |
| colour | tan | ✅ (could also be "cognac") |
| material | pebbled faux leather | ⚠️ |
| size | medium | ⚠️ |
| closure | not visible | ✅ |
| description | "add a strap for shoulder or crossbody wear" | ❌ no strap in the photo |
| seo_description | "for an optional strap" | ❌ same |
| tags | | ✅ |

Note: **this is the same bag as IMG_2429 in a different colour.** The model can't know
that from one photo. Relevant for W03·D1 (grouping) and later Shopify variants.

## 5. IMG_2461 — taupe textured top-handle bag

| Field | Value | Verdict |
|---|---|---|
| title | Structured Taupe Textured Top-Handle Handbag | ✅ |
| product_type | handbag | ⚠️ the other four similar bags were called "tote" |
| colour | taupe | ✅ |
| material | textured faux leather with smooth leather trim | ❌ front panel looks woven/canvas, not leather; also says "faux" and "leather" for the same bag |
| size | medium | ⚠️ |
| closure | zip | ⚠️ something at the top right edge, hard to confirm |
| description | woven-texture front, smooth trim, gold anchors, front plaque | ✅ |
| seo_description | | ✅ |
| tags | | ✅ |

🔍 Missed: the gold handle anchors have small crystals/rhinestones.
🔍 The plaque reads **"MISS ALITA"**: a visible brand. It obeyed "do not invent a
brand" by not naming it. Decide whether visible brands *should* be named.

---

## Patterns across all five

1. **Material is the weakest field.** Leather vs faux leather is never visible; the model
   picks one with confidence. One case (IMG_2461) is self-contradictory. → this needs a
   human-supplied value or a prompt rule ("say 'leather-look' unless told otherwise").
2. **Side rings become a strap.** Twice it promised a shoulder/crossbody strap that isn't
   in the photo. On a store page that's a false promise. → prompt rule: describe only
   what's included.
3. **Size has no scale.** Four of five are "medium" by default; one contradicts its title.
4. **Opinion tags** ("work bag", "neutral", "everyday") are added freely. Not wrong, but
   inconsistent from bag to bag.
5. **Not deterministic.** Same photo → different titles every run.
6. **Closure "not visible" works.** Where the top isn't shown, it said so instead of
   guessing. That instruction is worth keeping for other fields.

## Week 2 acceptance test

- `python -m json.tool` accepts the output for 5 of 5 photos (target: 3). ✅
- This file has 5 entries. ✅
