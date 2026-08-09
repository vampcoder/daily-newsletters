---
layout: post
title: "Why Prediction Is Now the Biggest Challenge in Self-Driving"
date: 2020-02-19 02:57:06 +0000
source: "Oliver Cameron"
category: "Tech & AI"
excerpt: "For years, object detection was the bottleneck in self-driving. But advances in deep learning have shifted the challenge to prediction—anticipating what other road users will do next. This post explains why prediction has overtaken perception as the field's hardest problem."
theme_gradient: "linear-gradient(135deg, #ff9800 0%, #f57c00 100%)"
image: "https://cdn.substack.com/image/fetch/w_1100,c_limit,f_auto,q_auto:good/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F561cac8b-cf37-4638-ab09-88d17d3c72d9_1100x220.png"
is_summary: false
key_takeaways:
  - "Perception was the primary hurdle before deep learning matured, but accuracy has since improved dramatically."
  - "The focus is now shifting from detecting objects to predicting their future behavior."
  - "Prediction is the next critical frontier for safe and reliable autonomous driving."
---

For the last decade, the majority of the conversation within the self-driving machine learning community has focused on object detection. How can we improve the ability of self-driving cars to detect and track all of the dynamic objects critical to safe navigation? In 2010, before Deep Learning became commonplace, perception stood as the primary limitation on the capabilities of self-driving cars. It was not acceptable for a 3-ton machine to have such a high rate of false positives and negatives. This is best exemplified by ImageNet classification accuracy, where the state-of-the-art solution achieved just 50% accuracy in 2010 (compared to 88% today). Although ImageNet classification is not an apples-to-apples comparison to the state-of-the-art in object detection, it does serve as a proxy to progress in computer vision.

Two years later in 2012, [AlexNet](http://email.mg2.substack.com/c/eJw1kNuOgyAQhp-m3GkAoeoFF82mfQ2DMFpSBMKhjW-_WHeTSf7JP5nTp2SG1cddBJ8yKgniZLS4cswYGZAWTJOBD8ikaYkAmzRW5FgAhTJbo2Q23h0NdCC0Q0-hxx5z3umOj6Tn_SjZOGO8LP08sG5cenSsmWTRBpwCAW-Iu3eArHjmHNKlu13oo0aQAWJqnQmpVerfqMoGyhqzyRUc5EZZmZJZ_g5pPiY_Gw0QGuXd29tyuNI2Dkr8Sv74-Ept0AsygmKKMSUjprzH15a0HD9GcrvfaYd7wm8_F4a3lbapzClL9WqV31AUxpgsa67rPQyvB5JvpRKZqm7FmbxP4ORsQZ-w8kn3-3veAwgHn2QhZ4ineRLEmKG6TPs60wlvTaWj5AbRu18WlpCE) was one of the first entrants to the ImageNet competition to utilize Deep Learning with Convolutional Neural Networks. AlexNet serves as perhaps the most influential paper in computer vision, after achieving state-of-the-art accuracy on ImageNet in 2012.

Deep Learning, whether applied to lidar, cameras, or radars, began to creep into self-driving technology around 2014. This instance of Google’s self-driving car yielding to a lady in a wheelchair chasing a duck with a broom served as a famous example of just how far perception technology had co