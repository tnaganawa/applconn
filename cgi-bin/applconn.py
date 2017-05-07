#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cgi
import os
import sys
import json
import urllib
import networkx as nx
from networkx.readwrite import json_graph
 
###
enable_ganglia=True
ganglia_url='http://127.0.0.1/ganglia/'
###
#pathprefix='/var/www/html/applconn/'
#json_filepath='/usr/local/applconn/applconn.json'
pathprefix='/var/tmp/applconn/'
json_filepath='/var/tmp/applconn/applconn.json'
##

def errorhtml(txt):
    print("Content-Type: text/html")
    print("")
    print("Error: " + txt)
    sys.exit(31)


def drawimage(filename):
    os.system('dot -Tsvg %s/%s.txt -o %s/%s.svg' % (pathprefix, filename, pathprefix, filename))


def main():
    # Initialize Graph
    G=nx.DiGraph()
    with open(json_filepath) as f:
        jsondata=json.loads(f.read())
        G=json_graph.node_link_graph(jsondata)

    ##
    fs=cgi.FieldStorage()

    if (not fs.has_key('key')):
        errorhtml('No key defined')
    key=fs['key'].value
    if (not key in G.nodes()):
        errorhtml('No Such key') 

    compute_mode="dfs" # "dfs", "distance"
    if fs.has_key("dfsmode"):
     compute_mode="dfs"
    elif fs.has_key("distancemode"):
     compute_mode="distance"
     if (fs.has_key('distance')): 
      distance=fs['distance'].value
     else:
      distance=None # infinite large number
     if (fs.has_key('graphtype')): 
      graphtype=fs['graphtype'].value # 'undirectional' or 'directional'
     else:
      graphtype='directional'
    elif fs.has_key("shortestpathmode"):
     compute_mode="shortestpath"
     if (fs.has_key('shortest_path_target')):
      shortest_path_target=fs['shortest_path_target'].value
     else:
      errorhtml("No shortest_path_target is given")
    else:
     errorhtml("No computation mode is specified")

    # if reversed is specified, create reversed graph
    if (fs.has_key('reversed')): 
        reversed=True
    else:
        reversed=False
    if (reversed):
        G=G.reverse()
    searchtags=['All']
    if (fs.has_key('SearchDev')): 
     searchtags.append('Dev')
    if (fs.has_key('SearchOps')): 
     searchtags.append('Ops')
    if (fs.has_key('SearchNet')): 
     searchtags.append('Net')
    for nodeid in G.nodes():
     if (not 'searchtag' in G.node[nodeid] or not G.node[nodeid]['searchtag'] in searchtags):
      G.remove_node(nodeid)

    if (not key in G.nodes()):
        errorhtml('No Such key in given search codition') 

    ## Compute Tree from key node
    if (compute_mode=="dfs"):
     st=nx.dfs_tree(G, key) # "st" means "spanning tree"

     # add other edge if other paths are there:
     for node1 in st.nodes():
      for node2 in st.nodes():
       if G.has_edge(node1, node2):
        st.add_edge(node1,node2)

    elif (compute_mode=="distance"):
     if (graphtype == "undirectional"):
      G=nx.Graph(G)
      st=nx.Graph()
     else:
      st=nx.DiGraph()
     if (distance == None):
      paths = nx.single_source_shortest_path(G, key)
     else:
      paths = nx.single_source_shortest_path(G, key, cutoff=distance)
     for target_node in paths.keys():
      st.add_path(paths[target_node])

    elif (compute_mode=="shortestpath"):
     st=nx.DiGraph()
     try:
      for path in nx.all_shortest_paths(G, key, shortest_path_target):
       st.add_path(path)
     except(nx.exception.NetworkXNoPath):
      errorhtml('No path found in given search codition') 

    ### add attribute
    for n in st:
     tmp = st.node[n]
     tmp['name'] = n
     if (enable_ganglia):
      try:
       metric_url='{0}/api/metrics.php?host={1}&metric_name=load_one'.format(ganglia_url, n)
       f = urllib.urlopen(metric_url)
       js=json.loads(f.read()) # {"status":"ok","message":{"metric_value":"0.51","units":" "}}
       f.close()
       if (js['status']=='ok'):
        load_one=float(js['message']['metric_value'])
        if (1.0 < load_one):
         tmp['color'] = '#ff634f'
        elif (0.5 < load_one < 1.0):
         tmp['color'] = '#ffde5e'
        else:
         tmp['color'] = '#e2ecff'
      except (IOError):
       pass # ganglia is not available

      #raise Exception, tmp['color']
      if (n.find('_cpu') > -1):
       tmp['href'] = '{0}/graph_all_periods.php?hreg%5B%5D={1}&mreg%5B%5D=cpu_&aggregate=1'.format(ganglia_url, n[:-4])
      else:
       tmp['href'] = '{0}?c=unspecified&h={1}'.format(ganglia_url, n)
     else: 
      if (G.node[n].has_key('color')):
       tmp['color'] = G.node[n]['color']
      if (G.node[n].has_key('href')):
       tmp['href'] = G.node[n]['href']

    # json output
    js=json_graph.node_link_data(st)
    with open('{0}/1.json'.format(pathprefix), 'w') as f:
        f.write(json.dumps(js, sort_keys=True, indent=4))
    
    ## Graphviz
    A=nx.nx_agraph.to_agraph(st)
    A.write('%s/1.txt' % (pathprefix))
    
    ## SVG
    drawimage('1')
    
    ## inline svg
    with open(pathprefix+'/1.svg') as svgfile:
        svgdata=svgfile.read()
    
    ## CGI
    print ("Content-Type: text/html")
    print ("")
    print ("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
                <meta charset="UTF-8">
                <title></title>
        </head>
        <body>
        <h2>graph</h2>
         %s
        <div id="data">
        <a href="../1.txt">Data</a>
        </div>
        <div id="d3">

    <div id="chart"></div>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.4.11/d3.min.js"></script>
    <link type="text/css" rel="stylesheet" href="../applconn.css"/>
    <script>var jsonpath="../1.json";</script>
    <script type="text/javascript" src="../applconn.js"></script>

        <a href="../1.json">d3-graph-data</a>
        </div>
        </body>
        </html>
        """ % (svgdata)
    )


if __name__ == "__main__":
    main()
