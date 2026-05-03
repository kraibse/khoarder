"""Idempotent seed: runs on every startup, inserts only when DB is empty."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.entry import Entry
from app.models.tag import Tag, entry_tags
from app.models.relation import Relation
from app.models.attachment import Attachment


def _id() -> str:
    return str(uuid.uuid4())


def _dt(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


COLORS = [
    "oklch(72% 0.08 200)",
    "oklch(65% 0.10 160)",
    "oklch(68% 0.07 30)",
    "oklch(60% 0.09 280)",
    "oklch(74% 0.06 80)",
    "oklch(62% 0.11 320)",
    "oklch(70% 0.08 120)",
    "oklch(67% 0.09 240)",
    "oklch(75% 0.05 50)",
    "oklch(63% 0.10 190)",
    "oklch(71% 0.07 340)",
    "oklch(66% 0.08 100)",
]


TOPICS_DATA = [
    {
        "slug": "cog-sci",
        "name": "Cognitive Science",
        "color": COLORS[0],
        "description": "Memory, attention, perception, and the architecture of mind. "
                       "Bridging neuroscience, psychology, and computation.",
    },
    {
        "slug": "climate",
        "name": "Climate Systems",
        "color": COLORS[1],
        "description": "Earth's climate machinery: feedback loops, tipping points, "
                       "ocean-atmosphere coupling, and paleoclimate records.",
    },
    {
        "slug": "typography",
        "name": "Typography",
        "color": COLORS[2],
        "description": "Type design, typesetting history, optical sizing, legibility research, "
                       "and the invisible craft behind readable text.",
    },
    {
        "slug": "ml-arch",
        "name": "ML Architecture",
        "color": COLORS[3],
        "description": "Transformer internals, scaling laws, mixture-of-experts, efficient training, "
                       "and the evolving landscape of foundation models.",
    },
    {
        "slug": "urban",
        "name": "Urban Morphology",
        "color": COLORS[4],
        "description": "How cities grow, contract, and reorganise. Street networks, "
                       "density gradients, informal settlements, and spatial justice.",
    },
    {
        "slug": "phil-mind",
        "name": "Philosophy of Mind",
        "color": COLORS[5],
        "description": "Consciousness, qualia, intentionality, and the hard problem. "
                       "Where analytic philosophy meets cognitive science.",
    },
]


ENTRIES_DATA = [
    # ── Cognitive Science ─────────────────────────────────────────────
    {
        "topic": "cog-sci", "type": "Article", "has_img": True, "img_height": 220,
        "img_color": COLORS[0], "days_ago": 2,
        "title": "Working Memory as a Bottleneck for Human Reasoning",
        "excerpt": "The capacity limits of working memory impose hard constraints on sequential "
                   "reasoning, analogy formation, and problem solving. New neuroimaging data "
                   "suggests the prefrontal cortex acts less as a storage buffer and more as "
                   "a dynamic gating mechanism.",
        "body": """<p>Working memory (WM) has long been cast as the workspace of the mind — a limited-capacity store where information is held and manipulated during complex cognition. The canonical Baddeley model posits a central executive coordinating two slave systems: the phonological loop and the visuospatial sketchpad. But neuroimaging at 7T resolution is complicating this picture.</p>

<p>Recent fMRI studies reveal that the prefrontal cortex (PFC) engages not so much in <em>storing</em> information as in <em>selecting</em> which representations from posterior cortex to amplify. This gating role explains why WM capacity correlates so strongly with fluid intelligence: both demand precise control over which information enters conscious access.</p>

<h2>The Four-Chunk Limit</h2>

<p>Cowan's revised estimate of four ± one chunks (rather than Miller's original seven ± two) better captures performance on interference-controlled tasks. The discrepancy traces to chunking efficiency: Miller's participants were allowed to exploit long-term memory structures, effectively compressing multiple items into single higher-order units.</p>

<blockquote><p>The fundamental limit may not be the number of items held, but the precision with which each representation can be maintained against interference from competing activations.</p></blockquote>

<p>This has direct implications for instructional design. Tasks requiring more than four interdependent steps routinely exceed WM capacity, forcing learners into a fragile chain of sub-goals that collapses under distraction. Worked examples and completion problems partially offload this cost by externalising intermediate states.</p>

<h2>Individual Differences and the g Factor</h2>

<p>WM capacity is among the strongest single predictors of g — psychometric general intelligence. Longitudinal studies show that WM training produces near-transfer gains (better performance on trained tasks) but far-transfer to untrained domains remains controversial. The neural mechanism for near-transfer appears to be more efficient gating rather than expanded storage capacity.</p>

<p>The practical upshot: WM is a bottleneck, not a container. Interventions that reduce extraneous cognitive load (chunking, worked examples, progressive complexity) will consistently outperform those that aim to expand raw capacity.</p>""",
        "word_count": 312, "read_time_min": 2,
        "tags": ["working memory", "prefrontal cortex", "reasoning", "cognition", "neuroscience"],
        "source_label": "Cognitive Neuroscience Review",
        "source_url": None,
    },
    {
        "topic": "cog-sci", "type": "Paper", "has_img": False,
        "img_color": COLORS[6], "days_ago": 8,
        "title": "Predictive Coding and the Bayesian Brain Hypothesis",
        "excerpt": "Friston's free-energy principle frames perception as hierarchical inference, "
                   "with higher cortical areas sending predictions downward and prediction errors "
                   "propagating upward. The framework unifies attention, learning, and action.",
        "body": """<p>The Bayesian brain hypothesis, formalised by Karl Friston as the free-energy principle, proposes that the brain minimises surprise — or more precisely, variational free energy, an upper bound on surprise — by continually predicting its sensory input and updating its generative model when predictions fail.</p>

<p>Under this framework, perception is not bottom-up feature detection but top-down inference: higher cortical areas send predictions down the hierarchy; lower areas compute prediction errors and propagate them upward. Attention modulates the precision (inverse variance) assigned to prediction errors, effectively up-weighting reliable signals.</p>

<p>The framework's power lies in its unification of seemingly disparate phenomena: repetition suppression, the MMN, binocular rivalry, interoceptive inference, and voluntary action all fall out of the same variational principle. Its weakness is empirical tractability — the framework's flexibility risks unfalsifiability.</p>""",
        "word_count": 148, "read_time_min": 1,
        "tags": ["predictive coding", "Bayesian brain", "Friston", "free energy", "perception"],
        "source_label": "Nature Reviews Neuroscience",
        "source_url": None,
    },
    {
        "topic": "cog-sci", "type": "Note", "has_img": False,
        "img_color": COLORS[9], "days_ago": 14,
        "title": "Dual-Process Theory: System 1 vs System 2 Revisited",
        "excerpt": "Kahneman's framework separates fast, automatic cognition from slow, effortful "
                   "deliberation. Recent critiques argue the dichotomy obscures a continuous "
                   "dimension of cognitive control rather than two discrete systems.",
        "body": """<p>Kahneman's System 1 / System 2 distinction popularised a genuine empirical insight: not all cognition is deliberate. Fast, automatic responses are evolutionarily ancient, heuristic-driven, and largely unconscious. Slow, effortful responses recruit working memory and executive control.</p>

<p>Critics note that the binary framing is a rhetorical simplification. Stanovich argues for a tripartite model distinguishing algorithmic mind (capacity) from reflective mind (disposition to override). Evans emphasises that System 1 is not a single system but a family of autonomous subsystems with different evolutionary histories.</p>

<p>The more productive framing may be <em>cognitive control</em> as a continuous dimension modulated by stakes, time pressure, expertise, and fatigue — rather than two discrete systems switching between modes.</p>""",
        "word_count": 133, "read_time_min": 1,
        "tags": ["dual process", "System 1", "System 2", "Kahneman", "heuristics"],
        "source_label": None, "source_url": None,
    },
    {
        "topic": "cog-sci", "type": "Excerpt", "has_img": False,
        "img_color": COLORS[4], "days_ago": 20,
        "title": "The Embodied Mind — Varela, Thompson & Rosch",
        "excerpt": "Cognition is not the representation of a pregiven world by a pregiven mind "
                   "but is rather the enactment of a world and a mind on the basis of a history "
                   "of the variety of actions that a being in the world performs.",
        "body": """<blockquote><p>Cognition is not the representation of a pregiven world by a pregiven mind but is rather the enactment of a world and a mind on the basis of a history of the variety of actions that a being in the world performs. — Varela, Thompson & Rosch, <em>The Embodied Mind</em>, 1991</p></blockquote>

<p>This passage crystallises the enactivist challenge to computationalism. Where cognitivism treats the mind as a symbol-manipulating program running on neural hardware, enactivism insists that cognition is constitutively embodied and enacted — sensorimotor coupling with the environment is not a precondition for cognition, it <em>is</em> cognition.</p>""",
        "word_count": 100, "read_time_min": 1,
        "tags": ["embodied cognition", "enactivism", "Varela", "phenomenology"],
        "source_label": "The Embodied Mind (MIT Press)", "source_url": None,
    },
    {
        "topic": "cog-sci", "type": "Article", "has_img": True, "img_height": 180,
        "img_color": COLORS[7], "days_ago": 30,
        "title": "Attention as a Resource: Load Theory and Its Discontents",
        "excerpt": "Lavie's load theory predicts that high perceptual load consumes attentional "
                   "capacity, leaving no resources for distractor processing. But recent "
                   "replication failures call into question the generality of the effect.",
        "body": """<p>Load theory (Lavie & Tsal, 1994) proposed a neat resolution to the early/late selection debate in attention research. When perceptual load is high, the visual system is saturated processing the task-relevant display, leaving no capacity to process distractors — hence early selection. When load is low, spare capacity inevitably leaks to distractors — hence late selection.</p>

<p>The theory generated hundreds of studies. It also generated controversy. Multi-lab replication attempts have found inconsistent effect sizes, and the distinction between perceptual load and cognitive load (executive demands) has proven difficult to operationalise cleanly.</p>

<p>What remains robust is the core finding that attention is a limited resource — where load theory struggles is in characterising the nature of that limit precisely enough to make falsifiable predictions across paradigms.</p>""",
        "word_count": 148, "read_time_min": 1,
        "tags": ["attention", "load theory", "Lavie", "cognitive capacity", "perception"],
        "source_label": None, "source_url": None,
    },
    {
        "topic": "cog-sci", "type": "Reference", "has_img": False,
        "img_color": COLORS[11], "days_ago": 45,
        "title": "Key Labs: Cognitive Neuroscience Research Groups",
        "excerpt": "A curated list of active research groups in cognitive neuroscience, "
                   "with notes on their current focus areas and recent publications.",
        "body": """<ul>
<li><strong>Dehaene Lab (Collège de France)</strong> — Consciousness, global workspace theory, neural signatures of awareness</li>
<li><strong>Friston Lab (UCL)</strong> — Free energy principle, active inference, computational psychiatry</li>
<li><strong>Badre Lab (Brown)</strong> — Hierarchical cognitive control, frontal lobe organisation</li>
<li><strong>Ranganath Lab (UC Davis)</strong> — Episodic memory, hippocampal-prefrontal circuit</li>
<li><strong>Posner Lab (Oregon)</strong> — Attention networks, alerting/orienting/executive control</li>
</ul>""",
        "word_count": 70, "read_time_min": 1,
        "tags": ["reference", "neuroscience labs", "research groups"],
        "source_label": None, "source_url": None,
    },
    {
        "topic": "cog-sci", "type": "Note", "has_img": False,
        "img_color": COLORS[2], "days_ago": 60,
        "title": "Spaced Repetition: The Forgetting Curve and Optimal Review",
        "excerpt": "Ebbinghaus's forgetting curve shows exponential decay of memory traces. "
                   "Spaced repetition exploits this by scheduling reviews at the moment "
                   "forgetting is about to occur, minimising reviews while maximising retention.",
        "body": """<p>Hermann Ebbinghaus's 1885 self-experiments produced the forgetting curve: retention decays exponentially with time, levelling off at a residual baseline. The key insight is that the decay rate depends on the <em>strength</em> of the memory trace — and each successful retrieval strengthens the trace, slowing subsequent decay.</p>

<p>Spaced repetition systems (SRS) operationalise this with a scheduling algorithm. The optimal spacing interval for a given card is the point at which retention would fall to ~90% — reviewing earlier wastes study time; reviewing later risks forgetting. SM-2 (the algorithm behind Anki) approximates this with an exponentially increasing interval multiplied by an ease factor derived from recall quality.</p>

<p>The practical implications are stark: massed practice (cramming) produces strong short-term performance and rapid long-term decay. Spaced retrieval produces weaker short-term performance and durable long-term retention. The effect size is among the largest in applied memory research.</p>""",
        "word_count": 175, "read_time_min": 1,
        "tags": ["memory", "spaced repetition", "Ebbinghaus", "learning", "retention"],
        "source_label": None, "source_url": None,
    },

    # ── Climate Systems ───────────────────────────────────────────────
    {
        "topic": "climate", "type": "Article", "has_img": True, "img_height": 200,
        "img_color": COLORS[1], "days_ago": 5,
        "title": "Atlantic Overturning Circulation: Tipping Point or Gradual Decline?",
        "excerpt": "AMOC weakening is among the most consequential potential tipping elements "
                   "in the climate system. Proxy records and model ensembles disagree on whether "
                   "the transition is abrupt or gradual — the stakes are high either way.",
        "body": """<p>The Atlantic Meridional Overturning Circulation (AMOC) is a large-scale ocean current that transports warm surface water northward and returns cold, dense water southward at depth. It is responsible for much of Europe's anomalous warmth relative to comparable latitudes and plays a central role in global heat and carbon cycling.</p>

<p>Freshwater influx from Greenland ice melt reduces the salinity — and therefore density — of surface waters in the North Atlantic, potentially weakening the density gradient that drives the overturning. Palaeoclimate records show that AMOC has collapsed abruptly in the past (Dansgaard-Oeschger events), triggering rapid regional temperature changes of 10-15°C within decades.</p>

<p>The key uncertainty is whether the current trajectory represents a gradual linear weakening or an approach to a bifurcation point beyond which collapse becomes self-sustaining. Recent statistical fingerprinting studies suggest AMOC may be closer to a tipping point than previously thought, but the methods are contested.</p>""",
        "word_count": 185, "read_time_min": 1,
        "tags": ["AMOC", "tipping points", "ocean circulation", "climate risk", "Greenland"],
        "source_label": "Nature Climate Change", "source_url": None,
    },
    {
        "topic": "climate", "type": "Paper", "has_img": False,
        "img_color": COLORS[8], "days_ago": 15,
        "title": "Permafrost Carbon Feedback: Magnitude and Timing",
        "excerpt": "Permafrost soils store roughly twice the carbon currently in the atmosphere. "
                   "Thawing releases CO₂ and methane on timescales that interact with — and "
                   "potentially amplify — anthropogenic forcing.",
        "body": """<p>Northern hemisphere permafrost contains an estimated 1,460-1,600 Pg of organic carbon, accumulated over millennia under frozen conditions. As permafrost thaws, microbial decomposition resumes, releasing CO₂ and, in waterlogged anaerobic conditions, the more potent greenhouse gas methane.</p>

<p>Earth system models consistently underestimate this feedback because they lack adequate representations of thermokarst dynamics, deep soil carbon, and abrupt permafrost thaw. Process-based estimates suggest 37-174 Pg C released by 2100 under high-emission scenarios — a range that reflects genuine process uncertainty rather than model inadequacy alone.</p>

<p>The timing matters as much as the magnitude: slow carbon release adds to the atmospheric burden but gives society time to adapt; abrupt release from thermokarst lakes or subsea permafrost could produce non-linear warming acceleration.</p>""",
        "word_count": 158, "read_time_min": 1,
        "tags": ["permafrost", "carbon feedback", "methane", "climate sensitivity", "Arctic"],
        "source_label": "Global Change Biology", "source_url": None,
    },
    {
        "topic": "climate", "type": "Note", "has_img": False,
        "img_color": COLORS[3], "days_ago": 25,
        "title": "Radiative Forcing vs Climate Sensitivity: Getting the Units Right",
        "excerpt": "Radiative forcing (W/m²) is not the same as climate sensitivity (°C per doubling "
                   "of CO₂). The distinction matters for communicating climate projections clearly "
                   "without conflating cause and response.",
        "body": """<p><strong>Radiative forcing (RF)</strong>: The change in net downward radiative flux at the tropopause due to a perturbation, before the climate system responds. Units: W/m². CO₂ doubling produces ~3.7 W/m² of RF.</p>

<p><strong>Equilibrium Climate Sensitivity (ECS)</strong>: The equilibrium global mean surface temperature change in response to a doubling of atmospheric CO₂. Units: °C. Best estimate from IPCC AR6: 3°C (likely range 2.5–4°C).</p>

<p><strong>Transient Climate Response (TCR)</strong>: Temperature change at the time of CO₂ doubling in a 1%/year increase scenario. Lower than ECS because slow feedbacks (deep ocean heat uptake) haven't equilibrated. Best estimate: 1.8°C.</p>

<p>The practical upshot: RF tells you how hard you're pushing the system; ECS tells you how far it will eventually move. Policy discussions often conflate them.</p>""",
        "word_count": 150, "read_time_min": 1,
        "tags": ["climate sensitivity", "radiative forcing", "ECS", "IPCC", "climate basics"],
        "source_label": None, "source_url": None,
    },

    # ── Typography ────────────────────────────────────────────────────
    {
        "topic": "typography", "type": "Article", "has_img": True, "img_height": 240,
        "img_color": COLORS[2], "days_ago": 7,
        "title": "Optical Sizing: Why Typefaces Need Different Designs at Different Scales",
        "excerpt": "A typeface designed for 72pt headlines is structurally different from one "
                   "optimised for 9pt captions. Optical sizing compensates for how stroke contrast, "
                   "aperture, and x-height ratio interact with reading distance and print resolution.",
        "body": """<p>When type was set in metal, each size had to be cut individually — and skilled punchcutters subtly adjusted letterform proportions at each size. The 6pt 'a' had heavier strokes, wider apertures, and a larger x-height ratio than the 72pt version of the same design. This wasn't laziness or error; it was sophisticated compensation for the optical effects of scale.</p>

<p>Digital type homogenised this: one master outline, scaled uniformly. The result is that most digital typefaces are designed for a mid-range size (10–14pt) and perform suboptimally at extremes. At small sizes, thin strokes disappear and tight spacing creates texture rather than individual letterforms. At large sizes, the proportions read as heavy and the spacing feels cavernous.</p>

<h2>Variable Font Optical Size Axis</h2>

<p>OpenType variable fonts introduced the <code>opsz</code> axis to formalise what metal type cutters knew intuitively. Fonts like Skolar, Freight, and the recently revived optical sizes of classic designs use this axis to automatically adjust stroke contrast, spacing, and x-height as size changes.</p>

<p>CSS now exposes this via <code>font-optical-sizing: auto</code>, which passes the computed font-size to the opsz axis. For body text, this is almost always the right default. For display headings where you want a specific aesthetic, explicit <code>font-variation-settings: 'opsz' 72</code> gives precise control.</p>""",
        "word_count": 230, "read_time_min": 1,
        "tags": ["optical sizing", "variable fonts", "type design", "legibility", "OpenType"],
        "source_label": "Fonts In Use", "source_url": None,
    },
    {
        "topic": "typography", "type": "Note", "has_img": False,
        "img_color": COLORS[10], "days_ago": 18,
        "title": "Leading: The Ignored Dimension of Typographic Rhythm",
        "excerpt": "Line spacing (leading) interacts with line length, x-height, and reading speed "
                   "in ways that most style guides reduce to a single ratio. The nuance is worth "
                   "understanding before cargo-culting 1.5× line-height across every project.",
        "body": """<p>Leading — originally the physical lead strips inserted between lines of hot metal type — determines the vertical rhythm of text. Too tight, and descenders collide with the ascenders of the line below, creating visual noise. Too loose, and the eye loses the thread between lines.</p>

<p>The conventional advice (1.4–1.6× the font size) is a reasonable starting heuristic but papers over meaningful interactions:</p>

<ul>
<li><strong>Line length</strong>: Longer lines benefit from more leading because the eye travels further on the return sweep.</li>
<li><strong>x-height</strong>: Typefaces with tall x-heights (like many sans-serifs) appear more tightly set at the same line-height ratio and may need more leading.</li>
<li><strong>Type size</strong>: Display sizes (36pt+) need proportionally less leading than text sizes.</li>
<li><strong>Script</strong>: Languages with ascenders, descenders, and diacritics in common characters (Polish, Vietnamese) need more breathing room than Latin English.</li>
</ul>

<p>The only reliable method is to set sample paragraphs, step back, and look.</p>""",
        "word_count": 192, "read_time_min": 1,
        "tags": ["leading", "line spacing", "typographic rhythm", "readability", "type basics"],
        "source_label": None, "source_url": None,
    },
    {
        "topic": "typography", "type": "Excerpt", "has_img": False,
        "img_color": COLORS[5], "days_ago": 35,
        "title": "The Elements of Typographic Style — Robert Bringhurst",
        "excerpt": "Typography exists to honor its content. Like oratory, music, dance, "
                   "calligraphy — like all the arts — typography is both craft and fine art. "
                   "Its craft is to give the text form. Its fine art is to transcend that purpose.",
        "body": """<blockquote><p>Typography exists to honor its content. Like oratory, music, dance, calligraphy — like all the arts — typography is both craft and fine art. Its craft is to give the text form. Its fine art is to transcend that purpose. — Robert Bringhurst, <em>The Elements of Typographic Style</em>, 3rd ed.</p></blockquote>

<p>Bringhurst's canonical manual remains the closest thing typography has to a shared reference text. The famous opening sentence sets the terms: typography is in service of language, and its ultimate ambition is to become invisible — to let meaning pass through without obstruction. Everything else in the book is in service of that proposition.</p>""",
        "word_count": 95, "read_time_min": 1,
        "tags": ["Bringhurst", "typographic style", "craft", "reference"],
        "source_label": "The Elements of Typographic Style", "source_url": None,
    },

    # ── ML Architecture ───────────────────────────────────────────────
    {
        "topic": "ml-arch", "type": "Article", "has_img": True, "img_height": 200,
        "img_color": COLORS[3], "days_ago": 3,
        "title": "Mixture of Experts: Scaling Laws at Sparse Activation",
        "excerpt": "MoE layers route each token to a subset of experts, keeping compute per "
                   "forward pass constant while scaling total parameter count. Mixtral and "
                   "GPT-4 report showed this is now production-viable at frontier scale.",
        "body": """<p>Mixture of Experts (MoE) replaces a dense feed-forward layer with a collection of 'expert' sub-networks and a routing mechanism that selects a small subset (typically 2 of N) for each token. The result: total parameter count scales with N, but compute per forward pass stays constant because only 2 experts activate per token.</p>

<p>The appeal is straightforward: model capacity (parameters) drives many capabilities, but compute (FLOPs) drives cost. MoE decouples them. Mixtral 8×7B has 47B total parameters but 13B active parameters per forward pass — closer in cost to a 7B dense model while approaching the quality of a 13B+ dense model.</p>

<h2>Routing Challenges</h2>

<p>The main engineering challenge is load balancing: without explicit regularisation, the router collapses onto a small number of experts, underutilising most of the capacity. Auxiliary load-balancing losses encourage uniform expert utilisation, but this introduces a training instability surface that dense models don't have.</p>

<p>Expert capacity — the maximum number of tokens routed to a single expert per batch — introduces a hard constraint. Tokens that exceed capacity are dropped or handled by a shared 'catch-all' expert. At training time this is manageable; at inference on long contexts it requires care.</p>""",
        "word_count": 220, "read_time_min": 1,
        "tags": ["MoE", "mixture of experts", "scaling", "transformers", "efficient training"],
        "source_label": "Mistral AI Technical Report", "source_url": None,
    },
    {
        "topic": "ml-arch", "type": "Paper", "has_img": False,
        "img_color": COLORS[7], "days_ago": 12,
        "title": "Attention Is All You Need — Annotated Reading Notes",
        "excerpt": "The original transformer paper introduced multi-head self-attention as the "
                   "core operation, dispensing with recurrence entirely. Reading notes on the "
                   "architecture decisions that turned out to be essential vs incidental.",
        "body": """<p>The 2017 Vaswani et al. paper introduced several ideas that have proven durable and several that have been quietly dropped in subsequent architectures.</p>

<p><strong>Durable</strong>: Multi-head self-attention (MHSA) as the core operation. Residual connections and layer normalisation. Positional encodings (though sinusoidal has been largely replaced by learned or RoPE). The encoder-decoder architecture for seq2seq tasks.</p>

<p><strong>Superseded</strong>: The specific sinusoidal positional encoding. Dot-product attention without modifications (Flash Attention, grouped-query attention now standard). The warm-up learning rate schedule as specified. The specific dimensionality choices (512/2048) — these were tuned for WMT translation, not general pretraining.</p>

<p>The core insight that proved generative: any position in the sequence can attend to any other position in O(1) operations (vs O(n) for RNNs), at the cost of O(n²) memory. This trade-off proved worth it up to the context lengths of the time; the quest to reduce the quadratic cost without losing the expressivity has driven a decade of architecture research.</p>""",
        "word_count": 195, "read_time_min": 1,
        "tags": ["transformers", "attention", "Vaswani", "self-attention", "architecture"],
        "source_label": "arXiv:1706.03762", "source_url": None,
    },
    {
        "topic": "ml-arch", "type": "Note", "has_img": False,
        "img_color": COLORS[0], "days_ago": 22,
        "title": "KV Cache: Why Long-Context Inference Is Memory-Bound",
        "excerpt": "The key-value cache stores per-layer attention projections across the context. "
                   "At long contexts and large batches, the KV cache dominates GPU memory usage "
                   "and becomes the binding constraint on throughput.",
        "body": """<p>During autoregressive generation, a transformer re-computes the full attention for every new token — unless you cache the key and value projections from previous tokens. The KV cache trades memory for compute, storing O(n_layers × seq_len × d_kv) values per sequence in the batch.</p>

<p>For a 70B parameter model with 80 attention heads and a 4096-token context, the KV cache at float16 is approximately 2 × 80 layers × 4096 tokens × 128 d_head × 2 bytes ≈ 10.7 GB per sequence. At a batch size of 8, that's 85.5 GB — more than most A100 configurations support alongside model weights.</p>

<p>This is why grouped-query attention (GQA) and multi-query attention (MQA) exist: by sharing key and value heads across groups of query heads, the KV cache size shrinks proportionally without degrading quality significantly. Llama 3 uses GQA with 8 key-value heads for all model sizes above 8B.</p>""",
        "word_count": 188, "read_time_min": 1,
        "tags": ["KV cache", "inference", "attention", "memory", "LLM efficiency"],
        "source_label": None, "source_url": None,
    },

    # ── Urban Morphology ──────────────────────────────────────────────
    {
        "topic": "urban", "type": "Article", "has_img": True, "img_height": 190,
        "img_color": COLORS[4], "days_ago": 10,
        "title": "Street Network Centrality and Urban Vitality",
        "excerpt": "Space syntax analysis reveals that streets with high betweenness centrality "
                   "attract more pedestrian movement, which in turn predicts retail survival, "
                   "crime patterns, and neighbourhood identity formation.",
        "body": """<p>Space syntax, developed by Hillier and Hanson at UCL, treats the urban grid as a graph and applies centrality metrics derived from network theory to predict movement and activity patterns. The key insight: the configuration of streets — not just their individual properties — determines which are naturally busy.</p>

<p>Integration (closeness centrality in angular analysis) predicts long-range pedestrian movement — which streets people pass through when crossing the city. Choice (betweenness centrality) predicts local movement — which streets people use when navigating between nearby origins and destinations.</p>

<p>Empirical studies across dozens of cities find strong correlations between high-integration streets and retail activity, and between high-choice streets and street crime. The mechanism is straightforward: natural surveillance increases with footfall. The policy implication is also clear but frequently ignored in car-centric planning: adding through-movement capacity (lanes, flyovers) to a street often increases vehicle speeds while eliminating the pedestrian activity that made the street economically viable.</p>""",
        "word_count": 175, "read_time_min": 1,
        "tags": ["space syntax", "street networks", "urban vitality", "pedestrian", "planning"],
        "source_label": "Environment and Planning B", "source_url": None,
    },
    {
        "topic": "urban", "type": "Note", "has_img": False,
        "img_color": COLORS[9], "days_ago": 28,
        "title": "Informal Settlements: What 'Slum Upgrading' Gets Wrong",
        "excerpt": "Top-down upgrading programmes often destroy the social networks and economic "
                   "structures that made informal settlements function. The literature on "
                   "community-led upgrading shows consistently better outcomes.",
        "body": """<p>The conventional response to informal settlements is 'slum upgrading': formalise tenure, provide infrastructure, and impose building codes. This approach has a mixed record because it treats informality as a problem of missing services rather than as a rational adaptation to exclusion from formal housing markets.</p>

<p>Studies of Kibera, Dharavi, and Paraisópolis consistently find that displacement — even to better-quality housing — severs social and economic networks that residents depend on. A woman relocated from Dharavi loses not just her home but her workshop, her client relationships, her childcare network, and her position in a credit rotation group. The new flat in the resettlement colony is smaller than her previous enterprise space.</p>

<p>Community-led upgrading (the approach championed by SPARC, SDI, and Cities Alliance) inverts this: communities lead the survey, design the intervention, and negotiate with the state as organised counterparties. Outcome data show higher satisfaction, lower displacement rates, and more durable physical improvements.</p>""",
        "word_count": 185, "read_time_min": 1,
        "tags": ["informal settlements", "slum upgrading", "housing", "community planning", "Global South"],
        "source_label": None, "source_url": None,
    },

    # ── Philosophy of Mind ────────────────────────────────────────────
    {
        "topic": "phil-mind", "type": "Article", "has_img": True, "img_height": 210,
        "img_color": COLORS[5], "days_ago": 6,
        "title": "The Hard Problem of Consciousness: Chalmers' Challenge",
        "excerpt": "Chalmers distinguishes easy problems (explaining cognitive functions) from the "
                   "hard problem: why any physical process is accompanied by subjective experience "
                   "at all. Thirty years on, no consensus solution exists.",
        "body": """<p>David Chalmers' 1995 paper 'Facing Up to the Problem of Consciousness' drew a distinction that has structured debate ever since. The 'easy problems' of consciousness — explaining attention, memory integration, reportability, voluntary control — are easy not because they are simple but because they are in principle tractable through the standard methods of cognitive science and neuroscience. Explain the mechanism, and you've explained the phenomenon.</p>

<p>The 'hard problem' is different in kind. Even a complete functional and neural account of how the brain integrates information, generates reports, and controls behaviour would leave open the question: why is any of this accompanied by subjective experience? Why is there something it is like to be a brain processing information, rather than nothing?</p>

<h2>Responses</h2>

<p><strong>Eliminativism</strong>: Deny that qualia exist as a coherent category (Dennett). The hard problem dissolves once we abandon a Cartesian conception of inner experience.</p>

<p><strong>Illusionism</strong>: Qualia exist but their intrinsic properties are systematically misrepresented by introspection (Frankish). We seem to have rich phenomenal properties; we don't actually have them.</p>

<p><strong>Panpsychism</strong>: Consciousness is fundamental and ubiquitous (Goff). Matter has proto-phenomenal properties from which complex consciousness emerges.</p>

<p><strong>Higher-order theories</strong>: A mental state is conscious iff it is represented by a higher-order mental state (Rosenthal). Sidesteps the hard problem by tying consciousness to a functional role.</p>

<p>None of these positions commands consensus. The hard problem remains hard.</p>""",
        "word_count": 265, "read_time_min": 2,
        "tags": ["consciousness", "hard problem", "Chalmers", "qualia", "phenomenology"],
        "source_label": "Journal of Consciousness Studies", "source_url": None,
    },
    {
        "topic": "phil-mind", "type": "Paper", "has_img": False,
        "img_color": COLORS[1], "days_ago": 16,
        "title": "Global Workspace Theory vs Integrated Information Theory",
        "excerpt": "GWT (Baars, Dehaene) and IIT (Tononi) are the two most discussed scientific "
                   "theories of consciousness. They make different empirical predictions and "
                   "rest on incompatible conceptual foundations.",
        "body": """<p>Global Workspace Theory (GWT), developed by Baars and elaborated by Dehaene as Global Neuronal Workspace Theory, proposes that consciousness arises when information is 'broadcast' via a global workspace — a fronto-parietal network — making it available to multiple specialised processors simultaneously. The neural signature is a late (>300ms) event-related potential called the P3b, seen in ignition events when stimuli exceed an access threshold.</p>

<p>Integrated Information Theory (IIT), developed by Tononi, takes a radically different approach. Consciousness is identical to integrated information, measured by Φ (phi) — a quantity capturing how much information a system generates over and above its parts. High Φ means high consciousness; systems that are modular (information in parts doesn't integrate) have low Φ regardless of complexity.</p>

<p>The theories lead to opposite predictions in key cases. Cerebellum: GWT predicts low consciousness (not part of the global workspace); IIT predicts high consciousness (enormous integration). Anesthesia: GWT predicts loss of ignition; IIT predicts reduction in Φ. A recent adversarial collaboration tested both: results were inconclusive, with each theory's proponents claiming partial support.</p>""",
        "word_count": 200, "read_time_min": 1,
        "tags": ["GWT", "IIT", "Tononi", "Dehaene", "consciousness theories"],
        "source_label": "Neuroscience of Consciousness", "source_url": None,
    },
    {
        "topic": "phil-mind", "type": "Note", "has_img": False,
        "img_color": COLORS[6], "days_ago": 40,
        "title": "Mary's Room and the Knowledge Argument",
        "excerpt": "Frank Jackson's thought experiment: Mary knows all physical facts about colour "
                   "vision but has never seen red. When she leaves her black-and-white room, "
                   "does she learn something new? The argument targets physicalism.",
        "body": """<p>Frank Jackson's 1982 Mary's Room argument: Mary is a brilliant neuroscientist who knows every physical fact about colour perception — the wavelengths, the cone responses, the neural pathways, the behavioural dispositions. She has always lived in a black-and-white room. One day she leaves and sees red for the first time.</p>

<p>Does she learn something new? Jackson's intuition: yes, she learns what it's like to see red — a phenomenal fact not captured by any physical description. Therefore, physicalism is false: there are facts about the world (phenomenal facts) not exhausted by physical facts.</p>

<p><strong>Physicalist responses</strong>:
<ul>
<li><em>Ability hypothesis</em> (Lewis, Nemirow): Mary gains an ability (to recognise, imagine, remember red), not a new propositional fact.</li>
<li><em>Old fact, new mode of presentation</em>: Mary gains a new way of representing a fact she already knew, not a new fact.</li>
<li><em>Phenomenal concepts strategy</em>: phenomenal concepts are distinct from physical concepts while referring to the same properties — no dualism follows.</li>
</ul></p>""",
        "word_count": 195, "read_time_min": 1,
        "tags": ["Mary's Room", "knowledge argument", "Jackson", "qualia", "physicalism"],
        "source_label": None, "source_url": None,
    },
]


ATTACHMENTS_DATA = [
    {"filename": "working-memory-review.pdf", "ext": "pdf", "size_bytes": 2_340_000},
    {"filename": "neuroimaging-data.csv", "ext": "csv", "size_bytes": 145_000},
    {"filename": "experiment-notes.md", "ext": "md", "size_bytes": 12_800},
    {"filename": "figure-1-raw.png", "ext": "png", "size_bytes": 890_000},
]


async def seed_if_empty(db: AsyncSession) -> None:
    result = await db.execute(select(Topic))
    if result.scalars().first() is not None:
        return  # already seeded

    # 1. Topics
    topic_map: dict[str, str] = {}  # slug → id
    for td in TOPICS_DATA:
        t = Topic(id=_id(), slug=td["slug"], name=td["name"], color=td["color"], description=td["description"])
        db.add(t)
        topic_map[td["slug"]] = t.id
    await db.flush()

    # 2. Tags (collect all unique names first)
    all_tag_names: set[str] = set()
    for ed in ENTRIES_DATA:
        all_tag_names.update(ed["tags"])

    tag_map: dict[str, str] = {}  # name → id
    for name in sorted(all_tag_names):
        tag = Tag(id=_id(), name=name)
        db.add(tag)
        tag_map[name] = tag.id
    await db.flush()

    # 3. Entries
    entry_ids: list[str] = []
    for ed in ENTRIES_DATA:
        e = Entry(
            id=_id(),
            topic_id=topic_map[ed["topic"]],
            type=ed["type"],
            title=ed["title"],
            excerpt=ed["excerpt"],
            body=ed.get("body", ""),
            word_count=ed.get("word_count", 0),
            read_time_min=ed.get("read_time_min", 1),
            has_img=ed.get("has_img", False),
            img_height=ed.get("img_height"),
            img_color=ed.get("img_color", COLORS[0]),
            source_label=ed.get("source_label"),
            source_url=ed.get("source_url"),
            created_at=_dt(ed.get("days_ago", 0)),
            updated_at=_dt(ed.get("days_ago", 0)),
        )
        db.add(e)
        entry_ids.append(e.id)

    await db.flush()

    # Associate tags via the association table
    for ed, entry_id in zip(ENTRIES_DATA, entry_ids):
        for tag_name in ed["tags"]:
            await db.execute(
                insert(entry_tags).values(entry_id=entry_id, tag_id=tag_map[tag_name])
            )

    # 4. Attachments on first entry
    if entry_ids:
        for ad in ATTACHMENTS_DATA:
            a = Attachment(
                id=_id(),
                entry_id=entry_ids[0],
                filename=ad["filename"],
                ext=ad["ext"],
                size_bytes=ad["size_bytes"],
                storage_path="",
                created_at=_dt(1),
            )
            db.add(a)

    # 5. Relations (backlinks + related)
    # backlinks: entries referencing the first cog-sci article
    backlink_sources = entry_ids[1:4]  # entries 1,2,3 → entry 0
    for src_id in backlink_sources:
        db.add(Relation(id=_id(), from_entry_id=src_id, to_entry_id=entry_ids[0], kind="backlink"))

    # cross-topic backlinks
    if len(entry_ids) >= 14:
        db.add(Relation(id=_id(), from_entry_id=entry_ids[13], to_entry_id=entry_ids[0], kind="backlink"))
        db.add(Relation(id=_id(), from_entry_id=entry_ids[14], to_entry_id=entry_ids[0], kind="backlink"))

    # related entries for the first article
    related_targets = entry_ids[4:7]  # entries 4,5,6
    for tgt_id in related_targets:
        db.add(Relation(id=_id(), from_entry_id=entry_ids[0], to_entry_id=tgt_id, kind="related"))

    # additional backlinks among other entries
    if len(entry_ids) >= 12:
        db.add(Relation(id=_id(), from_entry_id=entry_ids[7], to_entry_id=entry_ids[8], kind="backlink"))
        db.add(Relation(id=_id(), from_entry_id=entry_ids[10], to_entry_id=entry_ids[11], kind="backlink"))
        db.add(Relation(id=_id(), from_entry_id=entry_ids[2], to_entry_id=entry_ids[3], kind="backlink"))
        db.add(Relation(id=_id(), from_entry_id=entry_ids[5], to_entry_id=entry_ids[6], kind="related"))
        db.add(Relation(id=_id(), from_entry_id=entry_ids[9], to_entry_id=entry_ids[10], kind="related"))

    await db.commit()
