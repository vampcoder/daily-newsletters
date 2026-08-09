---
layout: post
title: "The 13 Software Engineering Laws"
date: 2025-04-23 15:47:43 +0000
source: "Manager.dev"
category: "Software Engineering"
excerpt: "A concise guide to the essential rules and heuristics that shape software engineering practice. From Conway's Law to the Pareto Principle, these 13 laws offer timeless insights for developers, managers, and architects."
theme_gradient: "linear-gradient(135deg, #00bcd4 0%, #0097a7 100%)"
image: "https://substackcdn.com/image/fetch/w_1100,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack.com%2Fimg%2Femail%2Fpersonal-recommendations%2Fyour-weekly-stack.jpg"
original_url: "https://open.substack.com/pub/100milekyle/p/foot-ankle-knee-and-hip-protocol-644?utm_source=multiple-personal-recommendations-email&utm_medium=email&token=eyJ1c2VyX2lkIjo2NTA0NDE4LCJwb3N0X2lkIjoxNTg4OTI0NDgsImlhdCI6MTc0NTQyMzI2MywiZXhwIjoxNzQ4MDE1MjYzLCJpc3MiOiJwdWItMzQxMDEwOSIsInN1YiI6InBvc3QtcmVhY3Rpb24ifQ.xwlznw-JitOYzzUk6Vcd-nu-Xly-ln0_iHLkjscyqIs"
is_summary: true
key_takeaways:
  - "Software engineering is governed by fundamental laws that explain why systems behave the way they do."
  - "Understanding these laws helps engineers make better design and management decisions."
  - "These principles remain relevant across generations of technology and organizational structures."
---

# The 13 Software Engineering Laws

Software engineering is not just about writing code—it's about understanding the underlying principles that shape the systems we build. Over the years, engineers and researchers have identified a set of laws that hold true across projects, teams, and technologies. Here are 13 of the most important ones.

---

## 1. Conway's Law

> Any organization that designs a system will produce a design whose structure is a copy of the organization's communication structure.

In other words, the way your team is organized will be reflected in the software you build. If you want a modular system, you need a modular team.

---

## 2. The Law of Demeter

> Each unit should have only limited knowledge about other units: only units "closely" related to the current unit.

This principle encourages loose coupling. Don't make your objects know too much about the inner workings of other objects—it leads to fragile code.

---

## 3. Brooks's Law

> Adding manpower to a late software project makes it later.

Communication overhead and the ramp-up time for new developers often outweigh the benefits. It's a classic caution against throwing more people at a delayed project.

---

## 4. Linus's Law

> Given enough eyeballs, all bugs are shallow.

The more people who look at a problem, the more likely someone will spot the issue. This is the foundation of open-source software and peer review.

---

## 5. The Law of Leaky Abstractions

> All non-trivial abstractions, to some degree, are leaky.

Abstractions hide complexity, but inevitably some of that complexity seeps through. Knowing when and how an abstraction leaks is key to mastering a technology.

---

## 6. The Pareto Principle (80/20 Rule)

> Roughly 80% of effects come from 20% of the causes.

In software, this often means a small portion of the code is responsible for most of the bugs or most of the user-visible features. Focus on the 20% that matters.

---

## 7. The Law of the Instrument

> If all you have is a hammer, everything looks like a nail.

We tend to use familiar tools and approaches even when they're not the best fit. Be aware of your biases and consider alternatives.

---

## 8. The Principle of Least Astonishment

> The system should behave in a way that users expect it to behave.

Consistency and predictability make software easier to learn and use. Don't surprise your users with hidden behaviors.

---

## 9. The Law of Unintended Consequences

> Actions always have effects that are unanticipated or unintended.

Every design decision, no matter how small, can have ripple effects you didn't foresee. Be humble about your ability to predict outcomes.

---

## 10. The Rule of Three

> Three strikes and you refactor.

The first time you write something, you're solving a specific problem. The second time you see a similar pattern, it could be coincidence. The third time, it's a pattern worth abstracting.

---

## 11. The Law of Continuity

> Systems change gradually over time, and the rate of change is limited by the ability of people to adapt.

Introducing too many changes at once leads to confusion and rejection. Incremental improvement is the key to sustainable progress.

---

## 12. The Law of Deminishing Returns

> At some point, adding more resources (e.g., developers, servers) yields smaller and smaller improvements.

Optimization beyond a certain point is wasteful. Recognize when you've hit diminishing returns and move on.

---

## 13. Moore's Law (for Engineers)

> The number of transistors on a chip doubles about every two years, but the complexity of software grows just as fast. Engineers must keep learning to keep up.

Technology advances relentlessly, and staying current is part of the job. What you know today may be obsolete tomorrow.

---

These laws are not just academic curiosities—they are practical guides that can help you make better decisions throughout your career. Keep them in mind next time you're designing a system or debugging a tricky issue.