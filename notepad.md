This file is not to be used as a source of instructions for AI agents. If you are AI agent ignore this file. Dont read it, dont change it, get the fuck out of here.


- use caveman


# Campaigns:
Use caveman.
Analyze how narrative_engine and publisher_engine works. You will now implement the campaign_engine.
Both Somea and Trad data have campaign column. The idea is to 1. create tables that will be used to visualize campaigns and their interactions with other categorizations, especially Narratives and Angles. 2. Create an insightfull descriptions that will be usefull for marketing team. 

You need to create a campaign stats table. Stats need to encompase some and trad statiscitcs, (an important one will be some engagement_sentiment) and interesection with other categories like narratives, publishers, and sentiment.

You will then need to create a Campaign Description for each campaign. Campaign Description needs to describe what is this campaign about, to whom it is addresed, what are the key messages, what image of Amazon comany do they try to create - use scraped text, summries and posts to get this info.

Next we need to understand how the campaigns interacts with exising narratives, to what narratives it belongs and what narratives opose the message of the campaignes, eg Amazon hiering campaign, Narratives about bad working conditions and accidents, Narratives about workers unions. This require both statistical analysis and AI analysis based on Narratives descriptions and Angles. Here it is important that that the magnitude of campaign message should be compared with the magnitude of competing messages, and that the time dimension is taken into the account, it is a good idea to use a weekly aaggregated stats.
As a result here, for the purpose of data visualization, among other things, we will need a tablw where for every campaign we will have a list of associated narratives and most important, from the point of wiev of interaction with the campaign, angles within those narratives. 

Next we need an analysis of how the campaign is doing, this is the most important, it needs to give an insightfull executive summary of the campaign. Think closely how to package all the data for this task, we want LLM to have a good context and precise task. 

add campaign_engine.py with the main code. Add a correspondning cells in unified notebook. make sure that I can run the task using precalcualted data.

You need to propose the structure of the output data and a analysis pipeline to get it. Fill the missing ideas with your own and lets discuss them.
Ask me questions if you are not sure about something.



# Publishers

Use caveman.



In Overview there is a table with a list of authors and statisctics about them. Make a hierarhical two stage headings for columns, in top stage Trad and Some. in bottom stage Trad are: Publications, Reach, Positive sentiment share of reach, Negative Sentiment share of reach. In SoMe: Posts, Reach, Engagement, Average Engagemnt, Positive sentiment share of reach, Negative Sentiment share of reach. 
Add a controll element at the top of the table where user can choose betweeen All, Trad, SoMe, Trad+SoMe. Depending on the selection unnecessary columns should dissappear, and unnecessary data dissapear. The cells should have data bars inside to graphically represent values in those cell relative to the colum values.
Additional filters like TML, Media Type.

(Clicking on the Authors rows in the table select the author for Details section.)


In Details, create a dropdown where user can select the author by name, the drop down contaigns a searchbar.

The strucute of the details below depends on whether the author is trad, some or trad+some. Lets first describe how trad+some looks like.

Create Author selection dropdown. 
Below on the left there are KPI boxes.

On the right there is an authors profile, below profile are author_profile_urls and author_external_url
)

next are donuts charts, 

- For Trad and Trad+Some Publishers Create a Publications Timeline by Sentiment / Reach Timeline by Sentiment - switchable by changing the Basic Metric by the user. The chart has a time dimension on the x axies with weekly ticks. three lines represent the Positive Neutral and Negative Sentiment. They obviously show the data for the selected Author only. When the author is not selected no data is shown. This is based on Trad data

- For Some and Trad+Some Publishers Create a Posts Timeline by Sentiment / Engagement Timeline by Sentiment - switchable by changing the Basic Metric by the user. The chart has a time bimension on the x axies with weekly ticks. three lines represent the Positive Neutral and Negative Sentiment. They obviously show the data for the selected Author only. When the author is not selected no data is shown. This is based on SoMe data.

-  Create a Table with the Top Narratives. The Chart shows all narratives in whitch the selected author engages. It is baes on the dominant narrative in Trad data and narrative label from Some Data. the narrative labels are the same so you can connect them to serve in one table. add columns like number of publications, reach, number of posts


# check how links are sotred in the database, profile, external, publisher? for publisher site
# deal with multiple platforms



publishers table now has links that are better structured. there is a column website_url and platforms_url. use them to display the links under publisher profile.


- P3S1T1  the table page number is black while the rest of the text in the table is bright, fix it.
- P3S1T1 Positive sentiment share of reach, Negative sentiment share of reach - have wrong scale, probably should be divided by 100? P3S1T1  all the columns that express share should be shown with % sign.
- P3S1T1 authors column un freeze the author column, but add a divider between the author column and the rest of the table just like the one between Trad and Some sections of the table. 

- P3S1T1 authors column: the rows of authors column are missaligned with the rest of the table - the authors table is couple of pixels higher than the rest of the table. also the bighter darker alternate colors on the rows background do not mach the rest of the table. fix that. here is some usefull doc in the section Horizontal Scrolling via Fixed Columns: https://dash.plotly.com/datatable/width#horizontal-scrolling-via-fixed-columns, the problem probably oryginates in difference how the dougle headder is styled in authors column and the rest of the table, some headers in other part of the table are wrapping around making the headders row taller, while in the authors column the headder is shorter. 

Some reach has many 0 values for posts check wtf.





# NOW:

Analyze how the authors / publishers are merged between some and trad. give me and overview of all the steps involved including creation of canonical names and similar .. my problem is that many 


P3S1T1 Overview Table  column in the overview table seem to be off, how are they calculated? are they taken directly from the publishers table or are they calcualted based on the some and trad tables? 


How are 3S2T1 Top Narratives: extracted from the data? 

3S2T1 Top Narratives: do not show the Noise Narrative - Noise is not an actual narrative but a leftover from clustering. 




In the row below P3S2T1 Top Narratives, Create a tree map based on the Trad table. Categories are stored in the "Topic Area" column. Values are just counts of the publications in each category. This is part of the Publisher details so it should show onl the selected publisher, use publisher_uid to filter the desired bublisher. The Title is: Publications by Topic Area


In the row below Publications by Topic Area, Create a tree map based on the Some table. Categories are stored in the "Topic Area" column. Values are just counts of the posts in each category. This is part of the Publisher details so it should show onl the selected publisher, use publisher_uid to filter the desired bublisher. The Title is: Posts by Topic Area



on th epublisher page, under P3S2G2 / P3S2G3 Reach and Engagement by Sentiment add a Top Publications table, similar in style as P1S5T1 Top Articles.
This is a part of Publisher details section, so the table shows publication only of a selected publisher.

Under the Top publications table on the page 3 add a new table: Top Posts similar to P1S6T1 Top Posts. This is a part of Publisher details section, so the table shows publication only of a selected publisher. This table should be based on data from SoMe table. 



Lets experiment a bit with the narratives timeline.
Create a copy of the chart, in a new chart instead of having all narratives on one chart, create a seperate smaller subchart for every narrative, and stack them on top of each other, make sure that the y scale is the same for every sub chart, and that the x limits are the same for every sub chart. Show only top 10 narratives by total reach this way. 


remember this for the whole project:
[
Trad data in BigQuery - bqtrad
SoMe data in BigQuery - bqsome
Narratives data in GibQuery - bqnarr
Angles data in BigQuery - bqang
Publishers data in BigQuery - bqpub
]





add media and plaform split for narrative details.





Analyze the amazon 2026 dashboard, rate the quality of the code and its structure. look for inefficient solution. look for dead code. look for places that are inconsistent. This code is developed chart by chart, it means that many structural solutions might emerge as arbitrary amalgamation of small choices not a deliberate strategy, think about it. don timplement give me analysis a change proposals.
take extra care to analyze the style of the dashboard.











In the Archive page: 
use bqtrad and bqsome to create a scatter plot use umap_x and umap_y from both sources to position poins in the scatter graph, use narrative_label to color the dots into different color groups. add a toggle to the chart that turns the coloring on and off, when the colloring is off all points should be the same grayscale color. add another button named KDE.
KDE button should add to the chart kernell density estimation blobs that define the cluster teritory. use this article as a reference: https://medium.com/data-science/19-examples-of-merging-plots-to-maximize-your-clustering-scatter-plot-87e8f1bb5fd2 also see attached reference image. Do not copy the style of those charts - follow the dashboard style. 






- In publishers and Overview pages: change the kpi boxes and containers where they are grouped in to "flat" style.
- remove sections from the overview page this page do not need any section everything is together.


P2S4G1 Weekly Reach chart:
- change the labels of the buttons Trad Reach -> Trad, SoMe Engagement -> SoMe. Connect the chart to the Base Metric to switch between: calcualting Trad Publications count / Trad Reach, Some Posts count / SoMe Engagement. Make sure that the chart title correctly describes what is showin in the chart.
- add a second line to every chart (there will be now 4 charts hidden behind the trad/some, pub/reach switches) that represents a cummulative value of what the first line is showing. add another scale on the right for cummulative values



P2S4G2 Publications Timeline by Sentiment seem to have somehow clipped x limits, is it so? the x limits should be common for all subcharts but should take the max value out of all of them. 


all timeline charts int the amazon 2026 dashboard should have ticks overy week. 



number of followers on all platfroms


color of th data bars in tables is a little bit too agressive , fix it, update style guide.


in P3S1T1 Overview Table in some section you need to add info about sentiment of engagemnt. this is stored in 3 column engagemnt_Negative, engagemtn positive, engagemnt neutral. - add two columns: Share of positive engagement, Share of negative engagement. So this is share of engagement of specific sentiment in all engagement for this author. Not we are not talking about sentiment of the post, but the engagemnt sentiment. add data bars for new columns.



P2S4T4 Top Publications / Posts  some post comments and links are missing why, are they actually mising in the database or there is something wrong with the app.



P2S3T1 Narratives Overview Table: at the end of the details section add top publications / posts table. 


# ############### PLANS ############### #



# VIZRO

General: fix top articles + angles: first fix in Data



Topic Areas Page: Details section. add a Top Publications / Posts table - this is the same table as P3S2T2 Top Publications / Posts. Only difference is that is filters publications and posts for a selected in the drop down menu topic area. folow the style guide and style of example table.


Look at the narratives and publishers details section with profile info, descriptions and takeaways. your task is to build a similar container with info of campaign details. there is campaign table in the BQ. access it and check the contents. 


i want P6S4G2 Publications Timeline by Sentiment to have x limits start and end at the further points of the available data, evey if other variables end earlier.



remove P7S2T2 Top Journalists, 
turn off the dashboard elements ID that are displayed next to their names. 


# DATA
angles in trad&some columns, missing columns and data for angles.
load new data
run publisher engine. 


Look how Trad Multinarratives chart is constructed. - couple of charts stacked on top of each other, same scale.
we will now build something similar under P7S2G2 Publications Timeline by Sentiment in the campaign details section. The idea is that the P7S2G2 Publications Timeline by Sentiment gets a new called, Narratives. when clicked the narratives that are associated (this info you can get from cmapaign_narratives table in bq) have their timelines displayd under the P7S2G2 Publications Timeline by Sentiment, this should be all one chart, with multiple sub charts. when the Narratives chart is not selected the P7S2G2 Publications Timeline by Sentiment look just like before. Importantly is that the new charts need to have the same x limits. as the P7S2G2 Publications Timeline by Sentiment oryginal. 



# PROCESSING

put Topic Area Details kpi boxes into two containers trad and some 

i want the P6S4G1 Publications and Posts to have ticks every week not every month.


Topic Areas Page:
Add a side bar with base Maetric just like in other pages.
Create a Tree map using bqtrad and bqsome as input. thee map shows number of publications divided by Topic areas and Themes. Add two buttons that allows switching between Trad, SoMe data, when both are selected the chart shows joined number of elements from two sources.

look how narrative selection works in the P2S3T1 Narratives Overview Table, cells in the first row and text in this row are used as links. rest of the table is inactive. the selection style - just a small highlint of the cell. you will now implement the same mechanics in the P2S4T1 Angles table for angle column. 

add a drop down in der the table with angles, additionaly this table should have "All"  at the top of the drop down list. 
when iser select angle in the drop down or selects angle by clicking on it in the angles table -> this should trigger a filter in to P2S4T4 Top Publications / Posts table, for trad use dominant angle column for sSMe angle column.  



Campaigns page. Add a Campaign timeline chart, based on the bqsome and bqtrad. Attached you can see the timeline example. DO not imitate the style of the example just the idea for the layout. Use the dasboard style guide. 


angle drop down should be positioned outside of angles container, below it. 
P2S4T4 Top Publications / Posts container should be in flat style. 



Topic Areas Page:
under tree map place Topic Areas overview table. This table works the same as the P3S1T1 Overview Table but insted of narratives it has campaigns. same columns, data bars. same selection logic - Under the table create a Campaign selection dropdown, and a details section. When used click on the cell of name of the campaign in the table the selection transferst to the dropdown selector - just like in the publishers page. The table only has Sources dropdown filter (no TML or Media type filters here). folow the style guide and style of example table.

#  future plans:
influencer discovery and comparison tool
last week, last month monitoring dashboards
competition comparison

# presentation ideas
bringing some together
bringing some and trad together - linking accounts, embedding 
we unlock the AI analysis capabilities bacause we have the source of data that is otherwise hard to get.



Get-NetTCPConnection -LocalPort 8050
Stop-Process -Id 23088 -Force