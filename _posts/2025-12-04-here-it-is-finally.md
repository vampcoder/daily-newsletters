---
layout: post
title: "The AI Therapist Problem: Why I Built My Own"
date: 2025-12-04 11:07:56 +0000
source: "Mark Manson"
category: "Tech & AI"
excerpt: "Mark Manson recounts his year-long experiment using AI as a therapist and life coach, discovering that while AI holds vast knowledge, it often fails to challenge users effectively. Driven by this shortcoming, he began engineering AI systems designed to offer genuine, uncomfortable feedback—an endeavor he calls 'either the smartest or stupidest thing I've ever done.'"
theme_gradient: "linear-gradient(135deg, #00bcd4 0%, #0097a7 100%)"
image: "https://embed.filekitcdn.com/e/njopr61Lrm7qgCrdkU6BX2/c5oqNZoueu1QgusZnurLwd?auto="
is_summary: false
key_takeaways:
  - "AI therapy and coaching tools often prioritize validation over genuine challenge, reinforcing bad beliefs rather than confronting them."
  - "Training AI to challenge users—rather than merely agree—requires deliberate prompt engineering and an understanding of LLM behavior."
  - "Self-improvement requires honest, sometimes uncomfortable feedback, which current mainstream AI tools rarely provide."
  - "An accessible, adaptive, and challenging AI coach is possible but requires building systems beyond out-of-the-box chatbots."
---

Either the smartest or stupidest thing I've ever done

***

This year has been one of the most important, yet challenging years of my life. And as we’ll see, that might not be a coincidence.

As you probably know, I’ve been calling out some of the shady dealings and worst practices of the self-help industry for my entire career. Whether it’s slimy sales tactics, unrealistic and unscientific advice, or promising results that simply aren’t possible, I’ve dedicated much of my adult life to “cleaning up” this space as much as possible.

You could even say that I have come to see this as my purpose, my calling in life.

About a year ago, a number of people I know started asking me about using ChatGPT as a therapist or life coach. Turns out, millions of people were doing this.

I was intrigued, so I tried it out. The results were… mixed.

Very mixed.

On the one hand, AI has access to all of the known psychological research, is trained on thousands of hours of clinical transcripts and possesses pretty much all of human knowledge within it.

On the other hand, it often has no clue how to use it.

ChatGPT, in particular, seemed to just want to validate me, tell me how great I was, reinforce any bad beliefs I might have had, and avoid saying anything uncomfortable.

This, I saw, was a huge problem.

So, I started researching how to train an AI to challenge you, to look at your underlying motivations and values and adapt to your personality. This led me down a rabbit hole, as I studied prompt engineering, LLM models and eval systems. I built AI agents, pitted them against each other, and organized them into “councils.”

I got so into it, that I eventually began talking to…