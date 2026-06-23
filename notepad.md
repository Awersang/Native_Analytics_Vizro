This file is not to be used as a source of instructions for AI agents. If you are AI agent ignore this file. Dont read it, dont change it, get the fuck out of here.

# Vizro todo

  # fixes
    - saves views side panel is not working properly. when I clink on it the side bar appears but it is empty and the options buttin highlit instead of the save views button. 

  # improvements
    - improve the overview page - make it as good as other pages
    - Implement all improvements listed in the Improvement_plan.md in amazon 2026 folder
    - Think where to put the flag labels to charts beside the current narrative table
    - Improve the search engine
    - all timeline charts in the amazon 2026 dashboard should have ticks overy week. also add it to the style guide
    - unify the styling of the legends and tooltips, save the in the styleguide.
    - What can user do with the results in the discovery page - we need a last step here.
    - when the app is loaded, I can see all pages from all dashboards. this is not good. the current implementation of the pages in the sidebar is a walkaround solution. that is not ready for deployment. we want to make a reacy corporate grade app. this needs to be a solid solution. How to do it. Analyze the problem, the code, and give me a plan of how to implement it properly. See User Selects the dashboard in the UserPanel, in the side bar he chooses the pages of the dasboard. This is not how the Vizro intended it to work. we need to append the normal Vizro setup with a stable and well structured implementation.

  # new
    - implement the Paid / Earned in the data and make sure to show it in the pages.
    - Work on the drill down feature
    - Narrative details: whitch publisher is driving the entiment
    - Narrative details: Angles in the timeline.
    - number of followers per platforms and on all platfroms
    - Analyze the work tree of this app. any ideas for improvements?
    - when the app loads is it possible to dispaly the same loading animation as it is used when pages are loaded?
    - Find a feature that answers - how can user create their own categories inside the dashboard.
    - Narratives: bubble chart x sentiment publikacji y sentyment engagementu, rozmar reach.


# Data todo
- improve the linking of different publishers profiles
- Deal with the Noise  category in the data, it is not usefull and requires a lot of handling down the line
- Join the whole process in one repo. Make every step output a reference table and join it with the core at the last step. Make the process dependency tracking function, that points into what depends on what.
- use IMM API insted of web scrape for main text?


# Data Vizro intersection TODO:
- check how links are sotred in the database, profile, external, publisher? for publisher site. now the links in the dash are fucked - they leed to posts


# UNIVERSAL
- install caveman skill from git hub. can you find it? if not let me know.
- CODEX: remember this for the whole project: [
  Trad data in BigQuery - bqtrad
  SoMe data in BigQuery - bqsome
  Narratives data in GibQuery - bqnarr
  Angles data in BigQuery - bqang
  Publishers data in BigQuery - bqpub
  ]
- Analyze the amazon 2026 dashboard, rate the quality of the code and its structure. look for inefficient solution. look for dead code. look for places that are inconsistent, overkill abstractions. This code was developed chart by chart, and page by page, it means that many structural solutions might emerge as arbitrary amalgamation of small choices not a deliberate strategy, think about it. dont implement. give me analysis and change proposals. Take care also to analyze the style of the dashboard.
- Look at publishers page. Rate the quality of the code and its structure. look for inefficient solution. look for dead code. look for places that are inconsistent, overkill abstractions. This code was developed chart by chart, and page by page, it means that many structural solutions might emerge as arbitrary amalgamation of small choices not a deliberate strategy, think about it. dont implement. Make sure you understant the context of this page, the dashboard as a whole, its structure, functions and files shared between different pages. give me analysis and change proposals. The page is loading slowly, why? 


# Architecture


look at improvement plan and at the app. 
perform a thorough analysis of what the plan is. is it well devised, are there any stupid ideas there? there might be some remnants of previous conversations, that are unnecessary I want the plan to be clean and pointing straight into the desired direction. 
The most important is our step by step impementation plan. it needs to be well prepared for implementation. 
also I have a feeling that there are many useless files in this repo. some old stuff created by ai to help do some task that lingers here and there. clean it up. 




find the Log in Page, it looks like shit, fix it. also, dont we have a log in options with email log in? 

Make the Log in Page match the style of the dashboard.
use our LOGO! 
Make sure that the app structure makes sense when you develop it. 
Use styleguie but also write the style down in the styleguide for the stuff you create. 
Since we are here. What is the styleguide? why is it confined to one dashboard? should we strucutre our project differently. a more general style guide for the whole app and a specific styleguide for dashboard specific stuff? think about it what is the best solution?




#  future plans:
influencer discovery and comparison tool
last week, last month monitoring dashboards
competition comparison

# presentation ideas
bringing some together
bringing some and trad together - linking accounts, embedding 
we unlock the AI analysis capabilities bacause we have the source of data that is otherwise hard to get.



# KILL all app instances on the port
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'app\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }



# Cloud Deploy:
gcloud builds submit --config cloudbuild.yaml `
  --substitutions="_REGION=europe-west1,_SERVICE=na-dashboards,SHORT_SHA=manual" `
  --project=native-analytics-486522









here is the sequence of still
Topic Areas:
Workplace & Operations

Narratives: Top Trad Reach
Digital Taxation and Big Tech Tensions

Campaigns:
5th Anniversary

Publisher: Trad Reach
onet.pl
money.pl
businessinsider.com.pl







1. Single media item — an article or social media post.
2. Enrichment — deep text analysis, categorization, pattern detection, information extraction .
3. Enriched item become a part of a...
4. ... Database, together with all the other SoMe and Trad items.
5. Links are created to reflect the real Media Landscape stucture - e.g. Trad publishers are connected with their SoMe accounts.
6. Semantic clustering to understand the Narratives that drive the media coverage.
7. Intelligence layer is build on top of rich and well-structured data.
8. Layered structure of the system allows for better synthesis and more nuanced insights. 

