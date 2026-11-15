/*
 * MEGA BITE content.
 * All entries below are PLACEHOLDER demo content – replace with your own.
 *
 * Article fields:
 *   id        unique slug used in the URL (#/post/<id>)
 *   title     headline
 *   summary   one or two sentences shown on the card
 *   category  must match one of `categories`
 *   date      YYYY-MM-DD
 *   minutes   estimated reading time
 *   body      array of paragraphs
 */
window.MEGABITE = {
  categories: ["Tech News", "AI Tools", "Gadgets", "How-To", "Explainers"],

  articles: [
    {
      id: "choose-an-ai-assistant",
      title: "How to choose an AI assistant for everyday work",
      summary: "A short checklist for comparing AI assistants: what you need them to do, what they cost, and what happens to your data.",
      category: "AI Tools",
      date: "2026-11-14",
      minutes: 4,
      body: [
        "Picking an AI assistant is easier when you start from the task, not the brand. Write down the three things you would hand off first: drafting emails, summarising documents, writing code, or something else.",
        "Next, compare the practical details: a free tier you can test properly, monthly pricing, file-size limits, and which apps it connects to.",
        "Finally, read the privacy settings. Check whether your conversations are used for training, whether you can delete history, and who can see shared workspaces."
      ]
    },
    {
      id: "on-device-ai-explained",
      title: "On-device AI, explained in plain language",
      summary: "What it means when a phone or laptop runs AI locally instead of sending everything to the cloud.",
      category: "Explainers",
      date: "2026-11-13",
      minutes: 5,
      body: [
        "On-device AI means the model runs on the hardware in your hand. Your data does not have to leave the device for the feature to work.",
        "The trade-offs are size and speed. Local models are smaller than the largest cloud models, but they respond without a network round trip and keep working offline.",
        "Expect a mix: quick, private tasks handled locally, heavier requests sent to the cloud."
      ]
    },
    {
      id: "speed-up-your-laptop",
      title: "Five quick wins to speed up a slow laptop",
      summary: "No reinstall needed: startup apps, storage, browser tabs, updates and power settings.",
      category: "How-To",
      date: "2026-11-12",
      minutes: 3,
      body: [
        "Start with startup apps. Disable anything you do not need the moment you sign in.",
        "Free up storage: a nearly full drive slows everything down. Clear downloads, empty the bin and uninstall apps you no longer use.",
        "Keep the browser lean, install pending updates, and switch to a balanced power plan. Restart weekly."
      ]
    },
    {
      id: "ai-writing-tools-guide",
      title: "AI writing tools: where they help and where they don't",
      summary: "Good for outlines and first drafts, weaker on facts and tone. A practical way to use them without losing your voice.",
      category: "AI Tools",
      date: "2026-11-11",
      minutes: 4,
      body: [
        "AI writing tools are strongest at structure: outlines, headings, rewording and shortening.",
        "They are weaker at facts, quotes and your personal voice. Always check names, numbers and claims yourself.",
        "A good routine: outline with the tool, write the substance yourself, then use it to tighten and proofread."
      ]
    },
    {
      id: "buying-a-smartphone",
      title: "Buying a smartphone: the specs that actually matter",
      summary: "Cut through the spec sheet: battery, software support, camera consistency and storage matter more than headline numbers.",
      category: "Gadgets",
      date: "2026-11-10",
      minutes: 5,
      body: [
        "Look at how long the maker promises software and security updates. That decides how long the phone stays safe and fast.",
        "Battery life in real use beats battery size on paper. Read reviews that test daily usage.",
        "Choose storage you will not outgrow. It is the one thing you cannot upgrade later."
      ]
    },
    {
      id: "passkeys-vs-passwords",
      title: "Passkeys vs passwords: should you switch?",
      summary: "Passkeys resist phishing and are easier to use. Here is how they work and where to start.",
      category: "Tech News",
      date: "2026-11-09",
      minutes: 4,
      body: [
        "A passkey replaces your password with a cryptographic key stored on your device, unlocked with your fingerprint, face or PIN.",
        "Because there is no shared secret to type in, phishing sites cannot steal it.",
        "Start with your email and bank accounts if they support passkeys, and keep a recovery option available."
      ]
    },
    {
      id: "ai-image-tools-basics",
      title: "AI image generators: getting better results with better prompts",
      summary: "Describe subject, style, lighting and composition. A simple prompt formula you can reuse.",
      category: "AI Tools",
      date: "2026-11-08",
      minutes: 3,
      body: [
        "Good prompts are specific. Name the subject, the setting, the style and the lighting rather than hoping the tool guesses.",
        "Iterate in small steps: change one thing at a time so you learn what each word does.",
        "Check each tool's licence terms before using generated images commercially."
      ]
    },
    {
      id: "cloud-storage-compared",
      title: "Cloud storage: free tiers vs paid plans",
      summary: "How to decide when the free allowance is enough and when paying for more space makes sense.",
      category: "Explainers",
      date: "2026-11-07",
      minutes: 4,
      body: [
        "Free tiers are fine for documents and a few photos. Video and full-resolution photo libraries fill them quickly.",
        "Before paying, clean up duplicates and large old files.",
        "If you do upgrade, pick the plan that bundles what you already use, and keep a second backup of anything irreplaceable."
      ]
    },
    {
      id: "wifi-troubleshooting",
      title: "Slow Wi-Fi? A 10-minute troubleshooting routine",
      summary: "Router placement, channel congestion, device limits and when to call your provider.",
      category: "How-To",
      date: "2026-11-06",
      minutes: 3,
      body: [
        "Move the router to a central, raised spot away from thick walls and appliances.",
        "Restart it, update its firmware and, on a crowded block, try a different channel or the 5 GHz band.",
        "If a wired test is also slow, the problem is the line, not your Wi-Fi. That is the time to contact your provider."
      ]
    }
  ],

  // Categories of AI tools shown on the "AI Tools" page.
  // `query` is the search term used to filter related articles.
  tools: [
    { icon: "✍️", name: "Writing & Content", desc: "Drafting, editing, summarising and rewriting.", query: "writing" },
    { icon: "💻", name: "Coding", desc: "Autocomplete, code review and debugging helpers.", query: "code" },
    { icon: "🎨", name: "Images & Design", desc: "Image generation, editing and design assistants.", query: "image" },
    { icon: "⚡", name: "Productivity", desc: "Assistants for email, notes, meetings and tasks.", query: "assistant" },
    { icon: "🎧", name: "Audio & Video", desc: "Transcription, voice, captions and video editing.", query: "video" },
    { icon: "🔎", name: "Research", desc: "Finding, reading and summarising sources.", query: "summaris" }
  ]
};
