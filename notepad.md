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





Analyze the amazon 2026 dashboard, rate the quality of the code and its structure. look for inefficient solution. look for dead code. look for places that are inconsistent, overkill abstractions. This code was developed chart by chart, and page by page, it means that many structural solutions might emerge as arbitrary amalgamation of small choices not a deliberate strategy, think about it. dont implement. give me analysis and change proposals. Take care also to analyze the style of the dashboard.



Loo







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


# DATA
angles in trad&some columns, missing columns and data for angles.
load new data
run publisher engine. 



# VIZRO

General: fix top articles + angles: first fix in Data




i want P6S4G2 Publications Timeline by Sentiment to have x limits start and end at the further points of the available data, evey if other variables end earlier.




Look at publishers page. Rate the quality of the code and its structure. look for inefficient solution. look for dead code. look for places that are inconsistent, overkill abstractions. This code was developed chart by chart, and page by page, it means that many structural solutions might emerge as arbitrary amalgamation of small choices not a deliberate strategy, think about it. dont implement. Make sure you understant the context of this page, the dashboard as a whole, its structure, functions and files shared between different pages. give me analysis and change proposals. The page is loading slowly, why? 


Here is an idea. User goes through the dasboard. Selects stuff, tweeks parameters. And get some sort of interesting results. He wants to save a specific view of a page for later use so that it is not getting lost, and he can go back to tihs specific view. Is this feasable in this dashboard? It could take a form of an extra side panel with saved items. When saving the user can name the saved view. the side panel works as a management tool wher saves can be renamed, deleted, and perhaps exported in some format.
what do you think about this idea. do not implement.


This is a experimental feture, create a toggle so that it can be turnedd on and off. Lets test this on the Overview page. In the top right corner of a chart/ table, add a small menu button. when clicked couple of options should apper. 
"Copy Image to Clipboard", "Copy Data to Clipboard", "Download Image", "Download Data". 




P8S1 Filters: similarity slider: it should be a float - or on case it could slow things down it sohudl have a resolution od 0.1


what is the best way to publish this app using gcloud? 


when the app loads is it possible to dispaly the same loading animation as it is used when pages are loaded?


# Savable views

Implement a generic "saved views" feature for a Vizro/Dash app in c:\Świetlik\NATIVE ANALYTICS\Vizro. The feature should work for any page without per-page configuration.

How it works:

At startup, traverse app.layout recursively to collect all interactive component IDs and their value props (Dropdown→value, Slider→value, RangeSlider→value, Checklist→value, RadioItems→value, DatePickerRange→["start_date","end_date"]). Filter out non-interactive or Vizro-internal components by heuristic (e.g. nav/tab components).
Use dcc.Store(id="saved-views-store", storage_type="local") to persist saves in browser localStorage. Schema: { "/page-path": { "save-name": { component_id: value, ... }, ... } }.
Add a collapsible side panel (Bootstrap dbc.Offcanvas or equivalent) with: a text input + "Save" button to name and save the current view; a list of saved views for the current page; per-item Rename, Delete, and Export (JSON download) actions.
Restoring a saved view writes the saved values back to each component via a callback (one Output per tracked component).
Constraints:

Generic: zero per-page or per-dashboard config needed beyond adding the panel to the app once.
Saves are scoped to the current page (dcc.Location pathname).
Export = download a JSON file of the saved view dict.
Style consistently with the existing dashboard (Bootstrap dark theme, existing CSS).
Read the existing app entry point and layout structure first to understand how to attach the panel and dcc.Store without breaking existing callbacks.

Adjust the component-type map or styling details before sending if needed.



# PROCESSING


here is an idea. User goes through the dasboard. Selects stuff, tweeks parameters. And get some sort of interesting results. Then he can click share button on the chart, a small manu ask to choose the platform with which the image of the chart will be shared. it can be a new email message, slack, whatsapp, or ather. What do you think about it? is it feasable? how does triggering of other aplications work in general through the browser, is it reliable, is it simple? 




P2S4T4 Top Publications / Posts - the selection of the angles is not working well often a selected angle in the P2S4T1 Angles is hown as having multiple publications but the angles table remains empty. 

P2S4T4 Top Publications / Posts - when a new angle is selected that do not have any contents in the table table that is currently dispalying, that is when I select angle thath is appearing only in the Some and my table is set to trad the table should switch to SoMe by itself. 



P6S2G1 Publications by Media Source and Topic Area  data labesl in the light mode are bright with dropshadow - this is shit. make the starting blocks of the data strands thicker.

discover page: results table
the row selects but only after the details are loaded, I want the whole row to get selected all at once when i click on it. just like the cell get selected now instantly on the click.


discover page: style article text, style reactions map in some details  ???


move P6S4T2 Top Journalists to the rigth from P6S4T1 Top Topic Area Publishers.



lets investigate how different elements of the discovery page are reloading. it seems to me that some elements are reloading for no purpose. when I clik on the item in the results table the filter section reloads - this seems unnecessary. Exlopre the subject and tell if there are any improvements to be made on this front.






here is an idea. 
user selects a specific Publication, we can now take the embedding of this article. and look for all publications within certain distance to the selected one. If this would be computationally too expensive we can use u_map insted. what do you think? 
the resulting articles will appear in the table below the article details box.



throughout the dashboard there are tables with trad and some data (top publications mostly) analyze what columns are used in them what is the underlying columns name in the bq. show me the summary. 

When reference is selected - single publication chosen by the user, this publication should get en extra symbol in the umap chart. let it be a small cross, keep the normal dot as well, and add the cross symbol. aditionaly a circle with the radius defined by the similarity slider should be drawn around this point. The circle works as aditional filter. The actual filtering logic do not need to pass throught the umap chart, the filter can be applied simply on the table using distance calculation in umap space. 


P8 page: the items in this section do not conform to the namin convention with the use of items IDs - fix that.

reference: change "No reference article selected. Use “Use as reference” on a publication's details." to "No reference article selected."

Similarity slider: remove the value dispay of the slider that is dispalyed on the right side of the slider. 

Publications details: for SoMe posts show full text, the same way it is shown for trad.


in post details: add engagement donut chart for Some posts, look how mini donut charts are styled in the kpi sections in this dashboard. 

when there is a selection made in in the P8S2G1 Narrative Clusters (UMAP) and user changes some filter in the filters section the P8S2G1 Narrative Clusters (UMAP) reloads thus loosing the selection. this is not the behavior we want. the chart can update its display of the datapoints but the selection region should stay unchanged. is this possible? also the position and zoom of the chart could stay unchaged when the update is triggered. that would keep it more user friendly. 


P2S4G3 Publications Timeline by Media Type / Platform: fix the yellow lines doing from the top week, the line should not be yellow but have the same color as other arrows - grey. the outline around the text can stay yellow. 
P2S4G3 Publications Timeline by Media Type / Platform:  the y=0 line should be gray same color as the x axis line but thicker- as thick as data lines.

lets work on the discovery page. 
add publications and posts table like the one at the bottom of all pages. with Trad SoMe switch. 
above it you will ad a drop downs that allow for filtering by: Source, Sentiment, Publisher. 
on the top of the chart add also a slider for selecting the time range. 


look at P2S4G2 Publications Timeline by Sentiment.
u will implement a new chart based on this one. 
idea: x axis it for time in weekly buckets, y axis is divided into two sectinos, from zero up is for trad from zero down is for some. both up and down show positive values. the data is split by media type for trad and by platform for some. create 2 versions of the chart. 1. the lines are independed from each other. 2. chart is presented as stacked area chart 
place the new charts under P2S4G2 Publications Timeline by Sentiment.


you need to add special data labels to the chart. select 5 publications with highest rech for trad and 5 for some. create a fag labels for those datapoints. the flag should have: publisher / author, reach.

discover page:
in the publication detals box ( top right corner ) add a button "use as reference" with some nice icon.
in the search box add to the right from the search bar a reference box where the reference article info will be displayed, there should also be clear option in this field. when user clicks on the artocles button use as reference the article short date, publisher and title should appear there. 
below the reference box sould be a slider called "similarity" - it will be used de define the distance in the umap space but dont wire it for now just make the ui and the logic for selecting reference image. 
style the Serach full text as a toggle not a checker box.

REname the ID of the umap to apropiate value.
I dont like thath between orange and blue the color appears to be gray.
when color by time is on there should be another toggle called relative that switches if the gradient is adjuested to the currently selected time window or to the whole data range. 
Color by narrative and time cannot be ON at the same time. 

remove Similar Articles table.


lets work on the discovery page. 
add publications and posts table like the one at the bottom of all pages. with Trad SoMe switch. 
above it you will add a drop downs that allow for filtering by: Source, Sentiment, Publisher. topic area, narrative
on the top of the chart add also a slider for selecting the time range with the precision of one day.
there should also be a search bar - user can type anyphrase and the results will show itels that has a matching phrases in ony of the fields - author, publisher title, main text/posts text
think carefully how it all works, how results are updated when categories are added or removed from filtering, and so on. follow the style guide. 


add a publication details section at the bottom of the discovery page.
now when user clicks on a row in the table (or any text in this row except for a link text) the details section should display info about the publication or post. Use your brain to create a nice detail section. some kpi boxes, text summary, link to the website, publisher, date, journalist. 


add to the u_map add timescale coloring, "Color by time" button next to color by narrative. Create a 3 color gradient that maps to the full time range of the data. and color the dots. create some sort of legend so thath the colors can be interpreted.

Similarity slider: name the starting point close and the ending far. remove the inviger value dispaly.
clear reference button is not worknig fix it. 
Rename Reference Article to Reference Publication
Search bar and Reference Article should split the width of the box 50-50.


Look at discovery page. Rate the quality of the code and its structure. look for inefficient solution. look for dead code. look for places that are inconsistent, overkill abstractions. This code was developed chart by chart, and page by page, it means that many structural solutions might emerge as arbitrary amalgamation of small choices not a deliberate strategy, think about it. dont implement. give me analysis and change proposals. Take care also to analyze the style of the dashboard.


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



here is the sequence of stills from a short animation that I want you to generate. 
idea:
1 single text / data point
2. it gets enriched using AI - insights are added to the data point
3. to simplify the animation the enrichment icon is added to the text to represent the text and its enrichment points
4. there is many text that are enriched this way
5. enriched data is clustered ( changing colors of the text icons)
6. enriched data linked together (connections on the left side of the items columns)
7. then there are further analysis drawn from the enriched and clustered data. 
8. then there are ever further analysis that is drawn on both data and lower level analysis. 
no audio - just video
keep the background white
smooth animation with pauses on each step.
clean minimalistic style, you can preserve the handwritten style of the lines a bit.