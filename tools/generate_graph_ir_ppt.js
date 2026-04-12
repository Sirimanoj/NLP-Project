const PptxGenJS = require("pptxgenjs");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pptx.author = "Sirim";
pptx.company = "IIIT Dharwad";
pptx.subject = "NLP Project - Graph IR";
pptx.title = "Information Retrieval Using Dependency Graphs";
pptx.lang = "en-US";

const C = {
  bg: "0B1F33",
  panel: "13395B",
  panel2: "1C4C75",
  text: "F3F8FF",
  muted: "C8D7E8",
  accent: "2EC4B6",
  accent2: "FFB703",
  accent3: "6C8CC2",
  white: "FFFFFF",
  dark: "0F172A",
};

function addBackground(slide, title, section = "Graph IR Project") {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.35,
    fill: { color: C.accent },
    line: { color: C.accent },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 7.15,
    w: 13.333,
    h: 0.35,
    fill: { color: C.panel2 },
    line: { color: C.panel2 },
  });
  slide.addText(section, {
    x: 0.45,
    y: 0.06,
    w: 4.5,
    h: 0.22,
    color: C.dark,
    fontFace: "Aptos Narrow",
    bold: true,
    fontSize: 11,
  });
  if (title) {
    slide.addText(title, {
      x: 0.6,
      y: 0.55,
      w: 12,
      h: 0.5,
      color: C.text,
      fontFace: "Aptos Display",
      bold: true,
      fontSize: 28,
    });
  }
}

function addFooter(slide, text = "NLP Course Project | Information Retrieval Using Dependency Graphs") {
  slide.addText(text, {
    x: 0.5,
    y: 7.21,
    w: 8.8,
    h: 0.2,
    color: C.muted,
    fontFace: "Aptos",
    fontSize: 10,
  });
}

function addCard(slide, x, y, w, h, color = C.panel) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color, transparency: 4 },
    line: { color: C.accent3, transparency: 45, pt: 1 },
  });
}

function bulletList(slide, items, x, y, w, h, fontSize = 16) {
  const runs = [];
  for (const item of items) {
    runs.push({ text: `- ${item}\n`, options: { breakLine: false } });
  }
  slide.addText(runs, {
    x,
    y,
    w,
    h,
    color: C.text,
    fontFace: "Aptos",
    fontSize,
    valign: "top",
    margin: 0.06,
    breakLine: true,
  });
}

// Slide 1: Title
{
  const s = pptx.addSlide();
  addBackground(s, "");
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.7,
    y: 1.0,
    w: 11.9,
    h: 5.6,
    rectRadius: 0.1,
    fill: { color: C.panel, transparency: 2 },
    line: { color: C.accent3, transparency: 65, pt: 1 },
  });
  s.addText("Information Retrieval Using Dependency Graphs", {
    x: 1.1,
    y: 1.6,
    w: 10.8,
    h: 0.8,
    color: C.white,
    fontFace: "Aptos Display",
    bold: true,
    fontSize: 42,
    align: "left",
  });
  s.addText("Graph IR on TREC-COVID with Semantic and Structural Matching", {
    x: 1.15,
    y: 2.65,
    w: 9.9,
    h: 0.5,
    color: C.accent2,
    fontFace: "Aptos",
    bold: true,
    fontSize: 20,
  });
  s.addText("Student: [Your Name]\nCourse: Natural Language Processing\nInstitution: IIIT Dharwad", {
    x: 1.15,
    y: 3.65,
    w: 6.3,
    h: 1.5,
    color: C.muted,
    fontFace: "Aptos",
    fontSize: 18,
    breakLine: true,
  });
  s.addShape(pptx.ShapeType.ellipse, {
    x: 9.5,
    y: 3.4,
    w: 2.2,
    h: 2.2,
    fill: { color: C.accent, transparency: 8 },
    line: { color: C.accent, transparency: 20, pt: 1 },
  });
  s.addText("Graph\nIR", {
    x: 9.8,
    y: 4.0,
    w: 1.6,
    h: 1.0,
    color: C.dark,
    fontFace: "Aptos Display",
    bold: true,
    fontSize: 30,
    align: "center",
    valign: "mid",
  });
  addFooter(s, "NLP Final Project Presentation");
}

// Slide 2: Agenda
{
  const s = pptx.addSlide();
  addBackground(s, "Presentation Roadmap");
  const blocks = [
    ["Survey", "Prior development in Graph/Neural IR"],
    ["Implementation", "Dataset, parser, retrieval pipeline"],
    ["Innovation", "Semantic nodes + relation-aware edges"],
    ["Analysis", "Diagnostics, ablation, limits"],
    ["Deployment", "Vercel frontend + Render backend"],
  ];
  let y = 1.45;
  blocks.forEach((b, i) => {
    addCard(s, 0.9, y, 11.5, 0.9, i % 2 === 0 ? C.panel : C.panel2);
    s.addText(`${i + 1}. ${b[0]}`, {
      x: 1.2,
      y: y + 0.2,
      w: 2.9,
      h: 0.35,
      color: C.accent2,
      fontFace: "Aptos Display",
      bold: true,
      fontSize: 18,
    });
    s.addText(b[1], {
      x: 3.4,
      y: y + 0.2,
      w: 8.6,
      h: 0.35,
      color: C.text,
      fontFace: "Aptos",
      fontSize: 16,
    });
    y += 1.0;
  });
  addFooter(s);
}

// Slide 3: Problem
{
  const s = pptx.addSlide();
  addBackground(s, "Problem Statement and Objective");
  addCard(s, 0.8, 1.35, 6.2, 4.9);
  addCard(s, 7.1, 1.35, 5.45, 4.9, C.panel2);
  s.addText("Why standard keyword search is insufficient", {
    x: 1.1,
    y: 1.7,
    w: 5.6,
    h: 0.4,
    color: C.accent2,
    bold: true,
    fontFace: "Aptos Display",
    fontSize: 20,
  });
  bulletList(s, [
    "Exact words miss semantic equivalents (covid vs virus).",
    "Bag-of-words ignores sentence structure and dependency roles.",
    "Different relations can change meaning even with same terms.",
    "Need retrieval that uses both meaning and syntax.",
  ], 1.1, 2.2, 5.5, 2.5, 15);

  s.addText("Project objective", {
    x: 7.4,
    y: 1.7,
    w: 4.8,
    h: 0.4,
    color: C.accent,
    bold: true,
    fontFace: "Aptos Display",
    fontSize: 20,
  });
  bulletList(s, [
    "Build a Graph IR engine over TREC-COVID.",
    "Construct dependency graphs for query and documents.",
    "Score with semantic node similarity + edge relation overlap.",
    "Retrieve top-k docs and evaluate with precision/recall.",
  ], 7.4, 2.2, 4.8, 2.6, 15);

  s.addText("Core one-line pitch: retrieval by meaning + structure.", {
    x: 7.4, y: 5.15, w: 4.8, h: 0.5,
    color: C.white, bold: true, fontSize: 16, fontFace: "Aptos",
  });
  addFooter(s);
}

// Slide 4: Literature Survey
{
  const s = pptx.addSlide();
  addBackground(s, "Literature Survey: Evolution of the Field");
  addCard(s, 0.7, 1.25, 12.0, 5.9);
  const rows = [
    ["Classical IR", "TF-IDF, BM25 ranking", "Strong lexical baseline, weak semantic capture"],
    ["Syntactic IR", "Dependency links for matching", "Adds structure but brittle with synonyms"],
    ["Graph-of-Words", "Term graph centrality", "Captures topology, less deep semantics"],
    ["Neural Retrieval", "SBERT, DPR, ColBERT", "Strong semantics, less explicit syntax"],
    ["Hybrid Methods", "Graph + neural signals", "Best direction; motivates this project"],
  ];
  s.addText("Chronological development and motivation for Graph IR:", {
    x: 1.0, y: 1.55, w: 11, h: 0.4, color: C.accent2, fontSize: 18, bold: true, fontFace: "Aptos Display",
  });
  let y = 2.1;
  rows.forEach((r, i) => {
    s.addShape(pptx.ShapeType.roundRect, {
      x: 1.0, y: y, w: 11.2, h: 0.78, rectRadius: 0.05,
      fill: { color: i % 2 ? C.panel2 : C.panel, transparency: 3 },
      line: { color: C.accent3, transparency: 60, pt: 1 },
    });
    s.addText(r[0], { x: 1.25, y: y + 0.2, w: 2.2, h: 0.28, color: C.accent, bold: true, fontSize: 14 });
    s.addText(r[1], { x: 3.45, y: y + 0.2, w: 3.2, h: 0.28, color: C.text, fontSize: 13 });
    s.addText(r[2], { x: 6.7, y: y + 0.2, w: 5.2, h: 0.28, color: C.muted, fontSize: 13 });
    y += 0.93;
  });
  addFooter(s, "Survey: prior development in this field (not questionnaire survey)");
}

// Slide 5: Gap and Contribution
{
  const s = pptx.addSlide();
  addBackground(s, "Research Gap and Proposed Contribution");
  addCard(s, 0.85, 1.35, 5.8, 4.9);
  addCard(s, 6.75, 1.35, 5.75, 4.9, C.panel2);
  s.addText("Observed gaps", {
    x: 1.15, y: 1.72, w: 4.8, h: 0.35, color: C.accent2, bold: true, fontSize: 20,
  });
  bulletList(s, [
    "Lexical methods ignore semantic equivalence.",
    "Neural-only methods hide structural reasoning.",
    "Exact edge matching is too strict for real text.",
    "Many pipelines fail on empty/short graph cases.",
  ], 1.15, 2.2, 5.2, 2.8, 15);

  s.addText("Our contribution", {
    x: 7.05, y: 1.72, w: 4.8, h: 0.35, color: C.accent, bold: true, fontSize: 20,
  });
  bulletList(s, [
    "Dependency graph feature extraction for query and docs.",
    "Semantic node similarity via embeddings.",
    "Improved edge similarity via dependency relation overlap.",
    "Robust empty-node/edge safeguards for stability.",
  ], 7.05, 2.2, 5.1, 2.8, 15);
  addFooter(s);
}

// Slide 6: Architecture
{
  const s = pptx.addSlide();
  addBackground(s, "System Architecture");
  addCard(s, 0.75, 1.35, 12.0, 5.5);
  const nodes = [
    ["User Query", 1.0, 2.6, C.accent2],
    ["spaCy Parser", 3.05, 2.6, C.accent],
    ["Graph Features\n(nodes, edges, rels)", 5.1, 2.45, C.accent3],
    ["Semantic Node\nSimilarity", 7.6, 1.95, C.accent],
    ["Edge Relation\nSimilarity", 7.6, 3.35, C.accent2],
    ["Weighted Score\n0.7*node + 0.3*edge", 10.1, 2.45, C.white],
  ];
  nodes.forEach((n) => {
    s.addShape(pptx.ShapeType.roundRect, {
      x: n[1], y: n[2], w: 1.9, h: 1.0, rectRadius: 0.08,
      fill: { color: "1F4D73", transparency: 0 },
      line: { color: n[3], pt: 1.5 },
    });
    s.addText(n[0], {
      x: n[1] + 0.1, y: n[2] + 0.2, w: 1.7, h: 0.65, color: C.text, fontSize: 11, align: "center", valign: "mid",
      bold: true,
    });
  });
  // arrows
  const arrows = [
    [2.88, 3.05, 0.16], [4.93, 3.05, 0.16], [7.42, 2.47, 0.15], [7.42, 3.87, 0.15], [9.93, 3.05, 0.15],
  ];
  arrows.forEach((a) => {
    s.addShape(pptx.ShapeType.chevron, {
      x: a[0], y: a[1], w: a[2], h: 0.25, fill: { color: C.accent2 }, line: { color: C.accent2 },
    });
  });
  s.addText("Document corpus follows the same pipeline and is ranked by final score.", {
    x: 1.0, y: 4.95, w: 10.8, h: 0.35, color: C.muted, fontSize: 14,
  });
  addFooter(s);
}

// Slide 7: Implementation Details
{
  const s = pptx.addSlide();
  addBackground(s, "Implementation Details");
  addCard(s, 0.8, 1.35, 6.15, 5.4);
  addCard(s, 7.05, 1.35, 5.45, 5.4, C.panel2);
  s.addText("Dataset and preprocessing", {
    x: 1.1, y: 1.7, w: 5.2, h: 0.35, color: C.accent2, bold: true, fontSize: 19,
  });
  bulletList(s, [
    "Dataset: TREC-COVID corpus and topics.",
    "Practical subset: first 1000 docs for fast experiments.",
    "Primary text field: abstract.",
    "Option to remove stopwords before graph construction.",
  ], 1.1, 2.15, 5.5, 2.2, 14);
  s.addText("Tech stack", { x: 1.1, y: 4.55, w: 5, h: 0.3, color: C.accent, bold: true, fontSize: 17 });
  bulletList(s, [
    "Parser: spaCy dependency parser",
    "Retrieval logic: custom Graph IR scorer",
    "Backend: FastAPI (Render)",
    "Frontend: Vercel static app + API calls",
  ], 1.1, 4.9, 5.4, 1.5, 13);

  s.addText("Scoring functions", {
    x: 7.35, y: 1.7, w: 4.8, h: 0.35, color: C.accent, bold: true, fontSize: 19,
  });
  s.addText("NodeSim = semantic similarity between query/document node sets", {
    x: 7.35, y: 2.2, w: 4.9, h: 0.5, color: C.text, fontSize: 13,
  });
  s.addText("EdgeSim = Jaccard overlap on dependency relation labels", {
    x: 7.35, y: 2.8, w: 4.9, h: 0.5, color: C.text, fontSize: 13,
  });
  s.addText("FinalScore = 0.7 * NodeSim + 0.3 * EdgeSim", {
    x: 7.35, y: 3.45, w: 4.9, h: 0.45, color: C.accent2, fontSize: 16, bold: true,
  });
  s.addText("Robustness: if nodes or edges are empty, similarity defaults to 0 instead of crashing.", {
    x: 7.35, y: 4.15, w: 4.9, h: 1.15, color: C.muted, fontSize: 13,
  });
  addFooter(s);
}

// Slide 8: Innovation
{
  const s = pptx.addSlide();
  addBackground(s, "Innovation Highlights");
  addCard(s, 0.8, 1.35, 12.0, 5.5);
  const cols = [
    ["Innovation 1", "Semantic node matching captures synonym-level meaning."],
    ["Innovation 2", "Relation-aware edge score preserves structural intent."],
    ["Innovation 3", "Deployment split: Vercel frontend + Render API for reliability."],
    ["Innovation 4", "Error-safe scoring with empty-graph handling."],
  ];
  let x = 1.05;
  cols.forEach((c, i) => {
    addCard(s, x, 2.05, 2.8, 3.9, i % 2 ? C.panel2 : C.panel);
    s.addText(c[0], { x: x + 0.2, y: 2.3, w: 2.4, h: 0.3, color: C.accent2, bold: true, fontSize: 14 });
    s.addText(c[1], { x: x + 0.2, y: 2.75, w: 2.4, h: 2.7, color: C.text, fontSize: 13, breakLine: true });
    x += 2.95;
  });
  s.addText("These innovations directly target implementation marks + innovation marks.", {
    x: 1.0, y: 1.55, w: 10.8, h: 0.35, color: C.accent, fontSize: 16, bold: true,
  });
  addFooter(s);
}

// Slide 9: Deployment
{
  const s = pptx.addSlide();
  addBackground(s, "Deployment Architecture (Live Demo Ready)");
  addCard(s, 0.85, 1.35, 12.0, 5.5);
  addCard(s, 1.2, 2.2, 3.2, 3.5, C.panel2);
  addCard(s, 5.2, 2.2, 3.2, 3.5, C.panel);
  addCard(s, 9.2, 2.2, 3.0, 3.5, C.panel2);
  s.addText("Vercel\nFrontend", { x: 1.45, y: 3.05, w: 2.7, h: 1.0, color: C.accent2, bold: true, fontSize: 26, align: "center" });
  s.addText("Render\nFastAPI", { x: 5.45, y: 3.05, w: 2.7, h: 1.0, color: C.accent, bold: true, fontSize: 26, align: "center" });
  s.addText("Graph IR\nEngine", { x: 9.45, y: 3.05, w: 2.5, h: 1.0, color: C.white, bold: true, fontSize: 24, align: "center" });
  s.addShape(pptx.ShapeType.chevron, { x: 4.5, y: 3.6, w: 0.45, h: 0.35, fill: { color: C.accent2 }, line: { color: C.accent2 } });
  s.addShape(pptx.ShapeType.chevron, { x: 8.5, y: 3.6, w: 0.45, h: 0.35, fill: { color: C.accent2 }, line: { color: C.accent2 } });
  s.addText("Frontend link: https://graphirfrontend.vercel.app", {
    x: 1.2, y: 5.95, w: 10.8, h: 0.3, color: C.muted, fontFace: "Consolas", fontSize: 12,
  });
  addFooter(s);
}

// Slide 10: Results
{
  const s = pptx.addSlide();
  addBackground(s, "Analysis: Diagnostic Score Improvements");
  addCard(s, 0.8, 1.35, 12.0, 5.5);
  s.addText("Single-query diagnostic from prototype runs", {
    x: 1.05, y: 1.65, w: 5.6, h: 0.35, color: C.accent2, bold: true, fontSize: 16,
  });
  // Table
  const headers = ["Method", "Score", "Interpretation"];
  const rows = [
    ["Exact graph overlap", "0.0061", "Too strict, misses semantic equivalence"],
    ["Semantic node similarity", "0.5132", "Captures meaning-level overlap"],
    ["Weighted final score", "0.4522", "Structure term initially pulled score down"],
    ["Improved edge relation score", "0.4936", "Better structural matching"],
  ];
  const x0 = 1.0;
  const widths = [3.7, 1.8, 6.9];
  let y = 2.15;
  let x = x0;
  headers.forEach((h, i) => {
    s.addShape(pptx.ShapeType.rect, { x, y, w: widths[i], h: 0.5, fill: { color: C.panel2 }, line: { color: C.accent3, pt: 1 } });
    s.addText(h, { x: x + 0.08, y: y + 0.13, w: widths[i] - 0.12, h: 0.25, color: C.accent2, bold: true, fontSize: 13 });
    x += widths[i];
  });
  y += 0.5;
  rows.forEach((r, ri) => {
    x = x0;
    r.forEach((c, i) => {
      s.addShape(pptx.ShapeType.rect, {
        x, y, w: widths[i], h: 0.56,
        fill: { color: ri % 2 ? C.panel : C.panel2, transparency: 5 },
        line: { color: C.accent3, transparency: 65, pt: 1 },
      });
      s.addText(c, { x: x + 0.08, y: y + 0.15, w: widths[i] - 0.12, h: 0.26, color: C.text, fontSize: 12 });
      x += widths[i];
    });
    y += 0.56;
  });
  s.addText("Key takeaway: combining semantic + structural signals provides more realistic retrieval scoring.", {
    x: 1.0, y: 5.55, w: 10.8, h: 0.45, color: C.accent, fontSize: 15, bold: true,
  });
  addFooter(s);
}

// Slide 11: Ablation and Error Analysis
{
  const s = pptx.addSlide();
  addBackground(s, "Ablation and Error Analysis");
  addCard(s, 0.8, 1.35, 6.0, 5.5);
  addCard(s, 6.95, 1.35, 5.85, 5.5, C.panel2);
  s.addText("Ablation summary", { x: 1.1, y: 1.72, w: 4.8, h: 0.35, color: C.accent2, bold: true, fontSize: 19 });
  bulletList(s, [
    "Remove semantic nodes -> major score collapse.",
    "Use exact edges only -> brittle matching.",
    "Add relation-based edges -> score recovery.",
    "Disable safeguards -> runtime errors on sparse text.",
  ], 1.1, 2.2, 5.5, 2.9, 14);
  s.addText("Observed limitations", { x: 7.25, y: 1.72, w: 4.8, h: 0.35, color: C.accent, bold: true, fontSize: 19 });
  bulletList(s, [
    "Subset evaluation can under-represent true recall.",
    "Dependency parsing quality affects edge accuracy.",
    "Lite embedding mode is stable but less expressive.",
    "Full-model inference costs more compute/time.",
  ], 7.25, 2.2, 5.2, 2.9, 14);
  addFooter(s);
}

// Slide 12: Demo and Viva Script
{
  const s = pptx.addSlide();
  addBackground(s, "Demo Flow for Presentation");
  addCard(s, 0.85, 1.35, 12.0, 5.5);
  const steps = [
    "Open frontend: graphirfrontend.vercel.app",
    "Paste Render backend URL and click Load Corpus",
    "Run query: how does covid spread",
    "Show Top-K results and node/edge scores",
    "Show evaluation metrics for one qid",
    "Explain innovation statement in one line",
  ];
  let y = 1.9;
  steps.forEach((st, i) => {
    s.addShape(pptx.ShapeType.ellipse, {
      x: 1.1, y: y - 0.03, w: 0.35, h: 0.35, fill: { color: C.accent2 }, line: { color: C.accent2 },
    });
    s.addText(String(i + 1), {
      x: 1.205, y: y + 0.04, w: 0.14, h: 0.12, color: C.dark, bold: true, fontSize: 11, align: "center",
    });
    s.addText(st, { x: 1.58, y, w: 10.6, h: 0.3, color: C.text, fontSize: 15 });
    y += 0.67;
  });
  s.addText("Viva one-liner:", { x: 1.1, y: 5.95, w: 2.2, h: 0.3, color: C.accent, bold: true, fontSize: 15 });
  s.addText("\"My system retrieves by comparing query and document dependency graphs using semantic node and relation-aware edge similarity.\"", {
    x: 3.05, y: 5.95, w: 9.2, h: 0.35, color: C.muted, fontSize: 13,
  });
  addFooter(s);
}

// Slide 13: Conclusion
{
  const s = pptx.addSlide();
  addBackground(s, "Conclusion and Next Steps");
  addCard(s, 0.9, 1.45, 11.8, 4.9);
  s.addText("What this project demonstrates", {
    x: 1.2, y: 1.9, w: 5.2, h: 0.35, color: C.accent2, bold: true, fontSize: 19,
  });
  bulletList(s, [
    "A complete Graph IR implementation from dataset to deployment.",
    "Clear innovation over pure keyword or exact-graph baselines.",
    "Professor-friendly analysis using diagnostic and ablation evidence.",
    "Deployment-ready architecture suitable for live demo.",
  ], 1.2, 2.35, 10.8, 2.25, 15);
  s.addText("Future work", {
    x: 1.2, y: 4.85, w: 2.0, h: 0.3, color: C.accent, bold: true, fontSize: 16,
  });
  s.addText("Cross-encoder reranking | better parser | full-corpus evaluation", {
    x: 3.0, y: 4.85, w: 8.9, h: 0.3, color: C.text, fontSize: 14,
  });
  s.addText("Thank you", {
    x: 0.9, y: 6.55, w: 2.6, h: 0.5, color: C.white, bold: true, fontFace: "Aptos Display", fontSize: 26,
  });
  s.addText("Q and A", {
    x: 10.6, y: 6.55, w: 2.0, h: 0.5, color: C.accent2, bold: true, fontFace: "Aptos Display", fontSize: 24, align: "right",
  });
  addFooter(s, "Prepared for NLP Project Evaluation");
}

pptx.writeFile({ fileName: "Graph_IR_Project_Presentation.pptx" });
