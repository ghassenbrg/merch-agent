# Creative And Artwork Requirements

## Default Product Requirement

For `standard_tshirt`, use the configured template:

- PNG dimensions: `4500x5400`
- transparent background required
- max file size: 25 MB
- placement: `large_front`
- avoid cropping
- maintain edge margin
- design should occupy enough area to avoid tiny-print rejection

Always read config before finalizing dimensions because other products differ.

## Creative Brief Fields

Each selected candidate needs:

- audience
- niche and subniche
- buyer occasion
- design concept
- visual hierarchy
- typography direction
- illustration/motif direction
- palette
- recommended shirt colors
- colors to avoid
- image prompt
- negative prompt
- compliance exclusions
- validation notes

## Shirt Color Decisions

Choose product colors that make the design readable:

- Light designs: black, navy, dark heather, asphalt, forest.
- Dark designs: white, silver, light blue, natural.
- Warm palettes: black, navy, olive, dark heather.
- Pastel/cute palettes: white, heather gray, light pink, light blue.
- Avoid recommending a shirt color too close to the main artwork color.

Do not rely on one shirt color only unless the design requires it.

## Image Generation Prompt Rules

The prompt should request:

- original standalone apparel graphic
- transparent background or transparent-background-ready composition
- no mockup
- no model/person wearing shirt
- no hanger, folded shirt, store scene, wall, frame, watermark, signature, brand logo
- crisp edges and high contrast
- centered composition with comfortable margins
- no copyrighted characters or trademarked references

Avoid:

- "in the style of" living artists
- celebrity likeness
- brand names
- exact competitor phrases
- protected characters

## Post-Generation Review

Inspect:

- subject matches brief
- text is readable and spelled correctly
- no unexpected logos/signatures/watermarks
- background can be made transparent
- no protected IP
- enough contrast on recommended shirt colors
- no critical detail near artboard edge

If text rendering is poor, regenerate or switch to a workflow where imagegen produces art without text and the backend/vector layer adds typography.
