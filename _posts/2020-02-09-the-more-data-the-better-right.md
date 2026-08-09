---
layout: post
title: "Why Data Moats in Self-Driving Cars Are Not as Powerful as You Think"
date: 2020-02-09 19:11:52 +0000
source: "Oliver Cameron"
category: "Tech & AI"
excerpt: "This newsletter challenges the common assumption that more data automatically leads to better machine learning models, especially in self-driving cars. Drawing on Voyage's experience with Active Learning, it explains how smart data curation and automated dataset optimization can outperform simply accumulating miles. The post also points to a16z's analysis of data moats as a must-read for founders."
theme_gradient: "linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%)"
image: "https://cdn.substack.com/image/fetch/w_1100,c_limit,f_auto,q_auto:good/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F561cac8b-cf37-4638-ab09-88d17d3c72d9_1100x220.png"
original_url: "http://email.mg2.substack.com/c/eJwlkNuOhCAMhp9muMMoiuIFF7sx8xqmQschi-BimYlvv7iTNGnT8_8ZIFxjOvUeD2L5wDQ7q3tZd12jmNWdbZRUzB3zIyFu4LymlJHtefHOALkYrgGhGtGypx5Ep3q0Qwsg0XSPxrRjM46D7O3SWgR2nZkhW4fBoMYXpjMGZF4_ifbj1n7dxL1YwPdRveIJK1aQKZYUGHIv5B4hBRdWDsHy9_PkIRIH77kFAu4ObhIWTZbjbwbPFXQtDFKZ_jEyp0Ut6mLlp6aRomqqWk7fqpdSTbWY7pO4dfW2iurIy0FgfioTN5a0c46gxBZTaVgvDP-VQmEufsvB0TljgMWj_QCiD9F_vXTuqC9JHokwfZIXtV71amTlmI1lZ9DRF4nJwIYphj9tRovY"
video_url: "http://email.mg2.substack.com/c/eJwlkEuOwyAMQE9TlhE4AZEFixlFvUZEwW3RJBCB0yq3H6eVbNny_zl4wkeph9tKI7E3rHOKzmg5DMqK6IaorLYitfleEVefFkd1R7HttyUFT6nkswGsgl48XQh9HO4RomGrFRgEpQCiZAXv7-JcM_s9JswBHb6wHiWjWNyTaGuX_ucCV5ZXWrF0oazs93aUo7GWr3AgQbKMalRKQ6c6qadfa7S2k4TpOsFlkOsDurbfGvnwd44Q1aWUyLMfsXLB48T4ZJhiZrvuOdExY_a3BeMXkL4f-dxLx4Yu47stSIT1GzypjTV2FLwsFp6ZXVkSEwW_Yi35H0iHc4E"
is_summary: true
key_takeaways:
  - "Larger datasets don't automatically yield smarter models—data quality and relevance matter more."
  - "Active Learning can help achieve strong model performance with relatively small, well-curated datasets."
  - "Designing intelligent, automated data optimization techniques can be a more defensible data moat than raw data volume."
---

Why data moats in self-driving cars are not as powerful as you may think, and more.

## Data Moats

Datasets fuel the many machine learning models powering a self-driving car. Surely the larger the dataset, the more intelligent your machine learning model is, right? Wrong! Let’s talk about why it’s not as clear cut as it may appear.

Since we don’t drive millions of miles at [Voyage](http://email.mg2.substack.com/c/eJwlUMuOhCAQ_Bo5GmDE4IHDbsz8huHROGQVDDQz8e8Xx6ST6vSrqtpqhDXlUx2pIKkF8hKcGgUdBiaJU4NjUkgSyuIzwK7DpjBXIEc1W7AaQ4rXApeMP8hLTZPx3no5TqOXtCE13nnBpKGMGsvIRbPo6gJECwrekM8UgWzqhXiU7vHT8WeLdzr1Cr2umEhQnHLaYmITY4L3rKdi_pWjEHKmfH7OvBvovvK-VFNQ27_epp1kFUJA3XIHuQ2sl_hvp2lfGu41BjwXiNps4G5beP_hqxLPA1SET9kAEfJdvLyOcpQTaWQutZtRpS00H1bvkFP8B2C1cjw), I’ve been asked *many* times what our data moat is. Last week, [we shared our answer with an in-depth post this week on our work with Active Learning](http://email.mg2.substack.com/c/eJwlkNuOhCAMhp9muMMoiuIFF7sx8xqmQschi-BimYlvv7iTNGnT8_8ZIFxjOvUeD2L5wDQ7q3tZd12jmNWdbZRUzB3zIyFu4LymlJHtefHOALkYrgGhGtGypx5Ep3q0Qwsg0XSPxrRjM46D7O3SWgR2nZkhW4fBoMYXpjMGZF4_ifbj1n7dxL1YwPdRveIJK1aQKZYUGHIv5B4hBRdWDsHy9_PkIRIH77kFAu4ObhIWTZbjbwbPFXQtDFKZ_jEyp0Ut6mLlp6aRomqqWk7fqpdSTbWY7pO4dfW2iurIy0FgfioTN5a0c46gxBZTaVgvDP-VQmEufsvB0TljgMWj_QCiD9F_vXTuqC9JHokwfZIXtV71amTlmI1lZ9DRF4nJwIYphj9tRovY), one of our data moats is in the intelligent and automated techniques to optimize our datasets, not in the dataset itself. In that post, we shared some of our work utilizing Active Learning to achieve strong model performance with relatively small datasets.

Before I share more about Active Learning, I highly encourage every founder to read [this post on data moats from Martin Cascado and Peter Lauten at A16Z](http://email.mg2.substack.com/c/eJwlUMuOwyAM_JpyawQUUjhw6Crqb0QEnBY1gQicrbJfv9BKlj3yazTjLMIj5cNsqSDZC-QxeNNLKgRTxBvhmZKKhDLOGWC1YTGYdyDbPi3BWQwptgOuGL-Qp_FX6tnMZzpdRT_DxVGhrQWuqKbaC0YazWh3HyA6MPAL-UgRyQ).