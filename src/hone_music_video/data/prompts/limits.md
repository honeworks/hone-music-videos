# The limits of the local models

## What the shots are made with

Each shot is made in two steps. First a still image (the shot's first frame) is drawn from your still
prompt, using reference pictures of the characters in it. Then a video model animates that still for
the length of the shot, guided only by your motion prompt. The video model cannot add anyone or
anything that is not in the still, and it works at a low resolution (about 832x480).

## Limits of the still image

- At most six reference pictures per shot (three on some image models). A shot can show at most two
  characters with their own references; more people appear only as unnamed extras (soldiers, crowd)
  without references.
- Describe what is in the frame, not the story behind it. Say what changes from the reference
  (age, clothes, hair, injuries) or the reference wins.
- Unusual objects (a mace with an ox's head) are drawn as the nearest common object unless a
  reference picture of the object exists. Prefer props that read clearly.
- No text, letters or signs in the image.
- Avoid overlapping bodies where motion happens, and tangled two-body contact poses (cradling,
  embracing, grappling): the video model merges the bodies and adds hands. Show one body clearly and
  the other beside it.
- Size, aspect ratio and frame rate are parameters of the models: never write them in a prompt.

## What no prompt makes the still models draw

Six kinds of fact failed under every prompt and every model tried (100 hard cases, 2026-10). Plan each
shot around them, never ask for them:

1. **A body's own side** (his LEFT hand, her RIGHT leg, an eyepatch on the LEFT eye): a close-up of that
   one hand or leg, or no side at all.
2. **A grip or a bite between two bodies** (jaws on a leg, a hand holding a wrist, a blade flat on a
   shoulder): the moment just before or after (the recoil, the mark it left), or a close-up of only the
   touching parts.
3. **More than three of a kind that must be counted** (seven candles, twelve guests, five wolves): three
   or fewer, or a number that doesn't matter ("candles along the table").
4. **A tear, a cut or a swollen eye**: only in a close-up of the face.
5. **Eyes meeting**: a two-shot at eye level; eyes on a small thing: the thing large in the frame.
6. **A movement state** (diving, sliding, a blade passing through): its frozen position (wings folded,
   head down, a hand's width above the water).

## Limits of the video

- One action and one camera move per shot. Combined moves (dolly and tilt) fail. If the camera does
  not move, write "static camera", or the model invents a drift.
- Describe motion and camera only; the picture is already in the still. Use concrete verbs: "she
  lowers her eyes", "the horse gallops left to right", "the veil lifts in the wind".
- Small, physical motion works best: wind, flames, a turn of the head, walking, riding. Fast
  or complex body motion (fighting with contact, dancing, hands manipulating objects, many people
  interacting) degrades into blur and melting limbs. Show a fight as a single clear move (a shield
  raised, a blow landing) and let the cut carry the action.
- **Faces must be large.** In a wide shot a face is only ~40 pixels tall and the eyes flicker and
  vanish. Any shot where a face must be recognisable is a medium shot, close-up or extreme close-up
  (set `faces: true`). Wide shots show people from behind, in silhouette, small in a landscape, or
  with faces turned away.
- The video model may turn a head towards the camera on its own. If a person must keep their back to
  the camera or not look at it, say so in the motion prompt ("she keeps her back to the camera").
- At most 8 seconds per shot; a single shot does not need to be split. Very short shots (under 2 s)
  give the motion no time to read.
- The video keeps the first frame's composition: the camera can push in, pull back, pan or track, but a
  new place or a new person cannot appear. A change of place is a cut.
- Hands holding small objects, reflections, mirrors and readable text are unreliable; avoid making
  them the point of a shot.
- No one speaks, sings, whispers or mouths the lyrics: there is no lip sync. The video model does not
  follow negations ("she does not speak", "her lips stay closed" make the mouth move), and naming a
  part of the face draws the motion there. So a motion prompt **never** names the mouth, lips, jaw,
  teeth, breath or breathing, speaking, singing, whispering, words or a voice, not even negated. A face
  that must not talk is described only through what does move, then "her face stays still": "her eyes
  glisten, a single tear runs down her cheek, she slowly lowers her gaze; her face stays still". A
  smile, a laugh, a roar or battle cry is one held moment in the still prompt, not a motion.
- Negations do nothing in a motion prompt: say what happens and what stays still, never what does not
  happen.
- Name what moves, how and in which direction, and who or what stays still ("he lies completely
  still", "the dagger lies still on the grass"): the video model moves anything left unsaid.
- Inserts use a simple camera move: a straight push-in, a pull-back or a pan; never a move "along" or
  "around" an object.
- No hands, people or objects enter the frame unless the shot plans it; keep it so by saying what stays
  still, never by a negation.
- Fire and smoke only at their sources ("the torch flames flicker"). Describe light as light ("the warm
  glow of the torches shifts on the helmet"), never attached to a person or object.
- Every moving crowd or group of animals gets an explicit state and direction ("the horses stand
  still, grazing", "riders walk slowly to the right"). A crowd of small figures gets a static camera,
  never a pan across it.
