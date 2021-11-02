#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#Import libraries
import pandas as pd
import numpy as np
import seaborn as sns
import re
import json
from pandas.io.json import json_normalize
import requests
from datetime import *
import plotly.express as px
import matplotlib.pyplot as plt
import plotly.figure_factory as ff
import plotly.graph_objects as go


# In[ ]:





# In[ ]:



import github
from github import Github
from github import InputGitTreeElement


# In[ ]:


get_ipython().system('pip install geopandas')
get_ipython().system('pip install pyrebase')
get_ipython().system('pip install geojsoncontour')

import pyrebase
import geopandas as gpd
import geojsoncontour


# In[ ]:


#Request text file from the South African Weather Services
filename =f"Rainfall log-{datetime.now():%Y-%m-%d %H-%m-%d}.txt"
url = "https://sawx.co.za/rainfall-reenval/daily-recorded-rainfall-data-figures-south-africa/daily-recorded-rainfall-data-figures-south-africa-inc.txt"
r = requests.get(url)
saws_data =r.text
saws_data = re.split('\n',saws_data)


# In[ ]:


#SAWS#
#Read file with SAWS Automatic Rainfall Stations names
ars = pd.read_csv(r"https://raw.githubusercontent.com/Zelbe04/research_project/main/synop_current_stations.csv",delimiter=",")
arslst= ars['StasName'].tolist()


# In[ ]:


#Extract all names and rainfall readings from textfile
res = [x for y in arslst
           for x in saws_data
               if re.search(y, x)]
readings = []
for item in res:
    for subitem in item.split():
        if(subitem.isdigit()):
            readings.append(subitem)
location = []
for x in res:
    location.append(x.strip(x[-4:]))
cleaned_location=[]
for x in location:
    cleaned_location.append(x.strip())


# In[ ]:


#Create a dataframe og just station names and their respective rainfall readings
saws_df = pd.DataFrame(zip(cleaned_location,readings),columns=['StasName','Rainfall'])


# In[ ]:


#Match latitiude and Longitude on names
saws_clean = pd.merge(saws_df,
                  ars[['StasName','Latitude','Longitude']],
                 on='StasName',
                 how= 'left')
saws_clean = saws_clean.fillna(0)
saws_clean['Rainfall'] = pd.to_numeric(saws_clean['Rainfall'])


# In[ ]:


#OpenWeatherMap API#
#Read Centroids and create index column in the dataframe

xy = r'https://raw.githubusercontent.com/Zelbe04/research_project/main/XY.csv'
xy = pd.read_csv(xy, delimiter=",")
xy['index'] = range(1,len(xy)+1)


# In[ ]:


#Current date to scrape the data
time = (datetime.now() - timedelta(1)).timestamp()
#Yesterdays date to use as object name when storing the data 
yesterday = datetime.now() - timedelta(1)                                                                                                                                                                                   
yesterday = datetime.strftime(yesterday, '%Y-%m-%d')


# In[ ]:


# Request data from OpenWeatherMap
output=[]
index=[]
for i in xy.itertuples():
    try:
        lat = i.ycoord
        lon = i.xcoord
        start = time
        end = time
        api_key =#Insert API key
        url =  "http://history.openweathermap.org/data/2.5/history/accumulated_precipitation?lat=%s&lon=%s&start=%s&end=%s&appid=%s&units=metric" % (lat, lon,start,end, api_key)
        response = requests.get(url)
        jsond = json.loads(response.text)
        df = pd.json_normalize(data=jsond['list'], 
                            meta=['date', 'rain','count']) #Normalize from JSON to dataframe
        output.append(df)
      
    except KeyError: #Skip rows that return Key error
        
        pass
output = pd.concat(output)


# In[ ]:


#Merge the lat and long of the centroids to the returned rainfall readings for the location
xy['index']= range(1,len(xy)+1)
output['index'] = range(1,len(output)+1)
ow =  pd.merge(output,
                  xy,
                 on='index',
                 how= 'left')
ow.drop(['date','count','index'],inplace=True, axis=1)
ow = ow.rename(columns={'rain': 'Rainfall','xcoord':'Longitude','ycoord': 'Latitude'})
ow = ow[['Rainfall','Latitude','Longitude']]


# In[ ]:


#Append the SAWS and OpenWeatherMap dataset
rainfall = saws_clean.append(ow)
rainfall= rainfall[rainfall['Rainfall'] > 0]
rainfall['StasName'] = rainfall['StasName'].fillna('NOT SAWS')


# In[ ]:


#ScatterPlot
#Create Grid
#rounding coordinates by chosen precision creates a grid
rounding_num=0.015 
rainfall["lon_mod"]=np.round(rainfall.Longitude/rounding_num,0)*rounding_num
correction_coeff=0.5
rainfall["lat_mod"]=np.round(rainfall.Latitude/(rounding_num*correction_coeff),0)*(rounding_num*correction_coeff)
rainfall["lon_mod"]=np.round(rainfall["lon_mod"],4)
rainfall["lat_mod"]=np.round(rainfall["lat_mod"],4)

# Creating grid dataframe with average unit prices for each tile. Excluding tiles with sample below 3 as insufficient samples. 
df_map=rainfall[["lat_mod","lon_mod","Rainfall"]].groupby(["lat_mod","lon_mod"], as_index=False).mean()
df_map.reset_index(inplace=True)
df_map["geo_Id"]=df_map.index
center_coors = -30.5595,22.9375


# In[ ]:


#Creating traces that contain the parameters to develop each layer on the map
data = [
    go.Scattermapbox(
            name="Scattermap",
            lat=df_map.lat_mod,
            lon=df_map.lon_mod,
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=df_map.Rainfall, 
                color=df_map.Rainfall,
                opacity=0.8,
                colorscale=["#7ecde0", "#2791e3" ,"#1709d9", "#10267d"],
                cauto=False,
                cmax=rainfall.Rainfall.max(),
                showscale=True),
                text=df_map.Rainfall
                
    ),
   go.Densitymapbox(
            name='Heatmap',
            lat=df_map.lat_mod,
            lon=df_map.lon_mod,
            z=df_map.Rainfall,
            
            radius=20, 
            colorscale=["#7ecde0", "#2791e3" ,"#1709d9", "#26008f"],
            opacity = 0.8
    )
]


# In[ ]:


#Parameters for map layout
layout = go.Layout(
    title="Daily Rainfall Reading in mm on the " + yesterday,  
    title_x=0.5,
    showlegend=True,
    legend=dict(
     yanchor='top',
        y=0.99,
        xanchor='left',
        x=0.01
    ),
    
    
    height = 750,
    # top, bottom, left and right margins
    margin = dict(t = 80, b = 0, l = 0, r = 0),
    font = dict(color = 'dark grey', size = 18),
 
    mapbox = dict(
       

        center = dict(
            lat = center_coors[0],
            lon = center_coors[1]
        ),
        # default level of zoom
        zoom = 5,
        # default map style
        style = "carto-positron"
    )

)  


# In[ ]:


#Creat map using the traces and layout parameters
figure = go.Figure(layout=layout,data=data)
figure = figure.update_traces(showlegend=True,selector=dict(type='densitymapbox'))
figure.write_html("/work/research_project/Map/index.html")


# In[ ]:


#Convert dataframe to json and Create Connection to Realtime database
rainfall_json = rainfall.to_dict(orient="records")
config = {
  "apiKey": #Obtained from your realtime datasbse",
  "authDomain": #Obtained from your realtime datasbse,
  "databaseURL": #Obtained from your realtime datasbse,
  "storageBucket": #Obtained from your realtime datasbse
}
 
firebase = pyrebase.initialize_app(config)


# In[ ]:


#Push rainfall data to database
db = firebase.database()
for index in range(len(rainfall)):
    db.child(yesterday).push(rainfall_json[index])
    
print("Data added to real time database ")


# In[ ]:


#Create connection to github repository 
g = Github(#Insert your API Key)
repo = g.get_repo(#Your repo directory)


# In[ ]:


#Push and commit the interactive map to github to allow the map to be hosted 
file_list = [
    "/work/research_project/Map/index.html"
]
file_name = ["index.html"]
commit_message = 'daily updated web map'

master_ref = repo.get_git_ref('heads/main')
master_sha = master_ref.object.sha
base_tree = repo.get_git_tree(master_sha)
element_list = list()

for i, entry in enumerate(file_list):
    with open(entry) as input_file:
       data = input_file.read()
    if entry.endswith('.png'): # images must be encoded
        data = base64.b64encode(data)
    element = InputGitTreeElement(file_name[i], '100644', 'blob', data)
    element_list.append(element)

tree = repo.create_git_tree(element_list, base_tree)
parent = repo.get_git_commit(master_sha)
commit = repo.create_git_commit(commit_message, tree, [parent])
master_ref.edit(commit.sha)


# <a style='text-decoration:none;line-height:16px;display:flex;color:#5B5B62;padding:10px;justify-content:end;' href='https://deepnote.com?utm_source=created-in-deepnote-cell&projectId=6b24e37a-71c0-476f-b5b1-2d8fe5101b64' target="_blank">
# <img alt='Created in deepnote.com' style='display:inline;max-height:16px;margin:0px;margin-right:7.5px;' src='data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB3aWR0aD0iODBweCIgaGVpZ2h0PSI4MHB4IiB2aWV3Qm94PSIwIDAgODAgODAiIHZlcnNpb249IjEuMSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB4bWxuczp4bGluaz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94bGluayI+CiAgICA8IS0tIEdlbmVyYXRvcjogU2tldGNoIDU0LjEgKDc2NDkwKSAtIGh0dHBzOi8vc2tldGNoYXBwLmNvbSAtLT4KICAgIDx0aXRsZT5Hcm91cCAzPC90aXRsZT4KICAgIDxkZXNjPkNyZWF0ZWQgd2l0aCBTa2V0Y2guPC9kZXNjPgogICAgPGcgaWQ9IkxhbmRpbmciIHN0cm9rZT0ibm9uZSIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPgogICAgICAgIDxnIGlkPSJBcnRib2FyZCIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoLTEyMzUuMDAwMDAwLCAtNzkuMDAwMDAwKSI+CiAgICAgICAgICAgIDxnIGlkPSJHcm91cC0zIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxMjM1LjAwMDAwMCwgNzkuMDAwMDAwKSI+CiAgICAgICAgICAgICAgICA8cG9seWdvbiBpZD0iUGF0aC0yMCIgZmlsbD0iIzAyNjVCNCIgcG9pbnRzPSIyLjM3NjIzNzYyIDgwIDM4LjA0NzY2NjcgODAgNTcuODIxNzgyMiA3My44MDU3NTkyIDU3LjgyMTc4MjIgMzIuNzU5MjczOSAzOS4xNDAyMjc4IDMxLjY4MzE2ODMiPjwvcG9seWdvbj4KICAgICAgICAgICAgICAgIDxwYXRoIGQ9Ik0zNS4wMDc3MTgsODAgQzQyLjkwNjIwMDcsNzYuNDU0OTM1OCA0Ny41NjQ5MTY3LDcxLjU0MjI2NzEgNDguOTgzODY2LDY1LjI2MTk5MzkgQzUxLjExMjI4OTksNTUuODQxNTg0MiA0MS42NzcxNzk1LDQ5LjIxMjIyODQgMjUuNjIzOTg0Niw0OS4yMTIyMjg0IEMyNS40ODQ5Mjg5LDQ5LjEyNjg0NDggMjkuODI2MTI5Niw0My4yODM4MjQ4IDM4LjY0NzU4NjksMzEuNjgzMTY4MyBMNzIuODcxMjg3MSwzMi41NTQ0MjUgTDY1LjI4MDk3Myw2Ny42NzYzNDIxIEw1MS4xMTIyODk5LDc3LjM3NjE0NCBMMzUuMDA3NzE4LDgwIFoiIGlkPSJQYXRoLTIyIiBmaWxsPSIjMDAyODY4Ij48L3BhdGg+CiAgICAgICAgICAgICAgICA8cGF0aCBkPSJNMCwzNy43MzA0NDA1IEwyNy4xMTQ1MzcsMC4yNTcxMTE0MzYgQzYyLjM3MTUxMjMsLTEuOTkwNzE3MDEgODAsMTAuNTAwMzkyNyA4MCwzNy43MzA0NDA1IEM4MCw2NC45NjA0ODgyIDY0Ljc3NjUwMzgsNzkuMDUwMzQxNCAzNC4zMjk1MTEzLDgwIEM0Ny4wNTUzNDg5LDc3LjU2NzA4MDggNTMuNDE4MjY3Nyw3MC4zMTM2MTAzIDUzLjQxODI2NzcsNTguMjM5NTg4NSBDNTMuNDE4MjY3Nyw0MC4xMjg1NTU3IDM2LjMwMzk1NDQsMzcuNzMwNDQwNSAyNS4yMjc0MTcsMzcuNzMwNDQwNSBDMTcuODQzMDU4NiwzNy43MzA0NDA1IDkuNDMzOTE5NjYsMzcuNzMwNDQwNSAwLDM3LjczMDQ0MDUgWiIgaWQ9IlBhdGgtMTkiIGZpbGw9IiMzNzkzRUYiPjwvcGF0aD4KICAgICAgICAgICAgPC9nPgogICAgICAgIDwvZz4KICAgIDwvZz4KPC9zdmc+' > </img>
# Created in <span style='font-weight:600;margin-left:4px;'>Deepnote</span></a>
