### File for format converters between libraries. Use if necessary ###
import os, glob

# Converts all tabs in a file to spaces. Yay.
def tabs_to_spaces(read_file,write_file):
	wf=open(write_file,"w")
	with open(read_file,"r") as rf:
		lines=rf.readlines()
		for line in lines:
			tokens=line.split("\t")
			w_str=" ".join(tokens)
			wf.write(w_str+"\n")
	wf.close()

# Convert multiplex edgelist file to netmem custom multiplex edgelist file.
# Expected format: first line-- max_node_id, max_layer_id. rest of file-- as is.
def multiplex_edge_to_netmem_multiplex(read_file,write_file):
	wf=open(write_file,"w")
	lines=[]
	max_node_id=0
	max_layer_id=0
	with open(read_file,"r") as rf:
		lines=rf.readlines()
		# First pass; Find max node id and layer id
		for line in lines:
			tokens=line.split(" ")
			# Format: layer n_src n_dst weight
			n1=int(tokens[1])
			n2=int(tokens[2])
			lid=int(tokens[0])
			if max_layer_id<=lid:
				max_layer_id=lid
			if max_node_id<=n1:
				max_node_id=n1
			if max_node_id<=n2:
				max_node_id=n2
		# Second pass: write header line, rest of file as is.
		wf.write(""+str(max_node_id)+","+str(max_layer_id)+"\n")
		for line in lines:
			wf.write(line)
	wf.close()

# Convert multiplex edgelist file to general multilayer edgelist file (MuxViz),
# 	in order for load() function to work properly with multiplex edgelists.
# Expected format for multiplex edgelist: layerID nodeSrc nodeDest weight
# Converting to format: nodeSrc layerID nodeDst layerID weight
def multiplex_edge_to_multilayer_edge(read_file,write_file):
	wf=open(write_file,"w")
	with open(read_file,"r") as rf:
		for line in rf.readlines():
			tokens=line.split(" ")
			wf.write(""+tokens[1]+" "+tokens[0]+" "+tokens[2]+" "+tokens[0]+" "+tokens[3])
	wf.close()


# Convert multiplex edgelist to multinet simple multiplex file, unweighted
def multiplex_edge_to_multinet_simple(read_file,write_file):
	wf=open(write_file,"w")
	with open(read_file,"r") as rf:
		for line in rf.readlines():
			tokens=line.split(" ")
			wf.write(""+tokens[1]+","+tokens[2]+","+tokens[0]+"\n")
	wf.close()

# Convert multiplex edgelist, layers, nodes file to multinet native file, in
# 	#TYPE multilayer mode
def multiplex_edge_to_multinet_full(read_actor,read_edge,read_layer,write_file):
	wf=open(write_file,"w")
	rf_actor=open(read_actor,"r")
	rf_edge=open(read_edge,"r")
	rf_layer=open(read_layer,"r")

	# Add multilayer header
	ml_header="#TYPE\nmultilayer\n"

	# Open layers file. Assume directed and no loops for benchmark.
	all_layers="#LAYERS\n"
	layer_lines=rf_layer.readlines()
	layer_count=0
	# Ignore header. No layer attributes. Assuming layer ids start from 1.
	for l in layer_lines[1:]:
		if l.strip()!="":
			layer_count=layer_count+1
	for i in range(1,layer_count+1):
		all_layers=all_layers+str(i)+",DIRECTED\n"

	# Open node attributes file. Assign header columns as attributes, all strings
	actor_attr="#ACTOR ATTRIBUTES\nnodeLabel,STRING\n"
	actor_lines=rf_actor.readlines()
	tokens=actor_lines[0].strip().split(" ")
	# Tokens assumed to be: nodeID nodeLabel [attbs]
	if len(tokens)>2:
		# Assuming all attributes are string.
		for t in tokens[2:]:
			t1=t.strip()
			actor_attr=actor_attr+t1+",STRING\n"
	# Add all actors & vertices
	all_actors="#ACTORS\n"
	all_vertices="#VERTICES\n"
	for a_line in actor_lines[1:]:
		a_tokens=a_line.strip().split(" ")
		# On multiplex edgelist, assume all actors are in all layers.
		all_actors=all_actors+(",".join(a_tokens))+"\n"
		for i in range(1,layer_count+1):
			all_vertices=all_vertices+a_tokens[0]+","+str(i)+"\n"

	# Add edge attribute: weight
	edge_attr="#EDGE ATTRIBUTES\nweight,NUMERIC\n"

	# Read all edges & weights
	all_edges="#EDGES\n"
	edge_lines=rf_edge.readlines()
	# No header- start writing immediately
	for e in edge_lines:
		# Convert multiplex edge (layer nodeSrc nodeDst weight) to 
		#	(nodeSrc layer nodeDst layer weight)
		e_tokens=e.strip().split(" ")
		e_line=",".join([e_tokens[1],e_tokens[0],e_tokens[2],e_tokens[0],e_tokens[3]])
		all_edges=all_edges+e_line+"\n"

	# Now write all into file
	wf.write(ml_header)
	wf.write(actor_attr)
	wf.write(edge_attr)
	wf.write(all_layers)
	wf.write(all_actors)
	wf.write(all_vertices)
	wf.write(all_edges)

	# ...and close the files.
	wf.close()
	rf_actor.close()
	rf_edge.close()
	rf_layer.close()
	return

# Converts from multinet file to multiplex node/edge/layer files.
# Does not convert attributes apart from node/layerLabel
def multinet_simple_to_multiplex_edge(read_file,write_nodes,write_edges,write_layers):
	actor_dict={}
	layer_dict={}
	actor_index=1
	layer_index=1
	# Open files
	rf=open(read_file,"r")
	wf_node=open(write_nodes,"w")
	wf_edge=open(write_edges,"w")
	wf_layer=open(write_layers,"w")

	# Get all lines
	mpx_lines=rf.readlines()
	header_check=mpx_lines[0].strip()

	# Check if header leads with #section, --comment or blank line. 
	# If so, assume a simple multiplex edge file and process. 
	if not(header_check=="" or header_check[0]=="-" or header_check[0]=="#"):
		# For each edge:
		for line in mpx_lines:
			if line.strip()!="":
				# Break if section start
				if line[0]=="#":
					break
				# Ignore comment lines
				if line[0:2]=="--":
					continue
				# Format for simple multiplex: nodeSrc nodeDst layer
				tokens=line.split(",")
				# Save node and layer labels into dictionary for later retrieval.
				# 	Searching through a list would be VERY costly.
				ns_ind=-1
				nd_ind=-1
				l_ind=-1
				# For nodeSrc:
				if tokens[0] not in actor_dict:
					actor_dict[tokens[0]]=actor_index
					ns_ind=actor_index
					actor_index=actor_index+1
				else:
					ns_ind=actor_dict[tokens[0]]
				# For nodeDst:
				if tokens[1] not in actor_dict:
					actor_dict[tokens[1]]=actor_index
					nd_ind=actor_index
					actor_index=actor_index+1
				else:
					nd_ind=actor_dict[tokens[1]]
				# For layer:
				if tokens[2] not in layer_dict:
					layer_dict[tokens[2]]=layer_index
					l_ind=layer_index
					layer_index=layer_index+1
				else:
					l_ind=layer_dict[tokens[2]]

				# Write found edge into edgefile. Assign weight=1
				# Format: layer nodeSrc nodeDst weight
				edge_str=str(l_ind)+" "+str(ns_ind)+" "+str(nd_ind)+" 1\n"
				wf_edge.write(edge_str)

	# Otherwise: only check type section (options: multiplex, multilayer) for format.
	# 	Drop all other attributes and additional actors not in edgefile.
	# 	WARNING: if weight is coded as an attribute, it will not be parsed. 
	else:
		# net_type by default 0 for multiplex, set to 1 for multilayer.
		net_type=0
		line_count=0
		# Check lines to find #TYPE section
		for line in mpx_lines:
			# If #TYPE found:
			if "#TYPE" in line or "# TYPE" in line:
				# Try to find "multilayer" on same or next line. If not found, assume multiplex.
				if "multilayer" in line.lower():
					net_type=1
					line_count=line_count+1
					break
				elif "multilayer" in mpx_lines[line_count+1].lower():
					net_type=1
					line_count=line_count+2
					break
				elif "multiplex" in line.lower():
					net_type=0
					line_count=line_count+1
					break
				elif "multiplex" in mpx_lines[line_count+1].lower():
					net_type=0
					line_count=line_count+2
					break
			line_count=line_count+1
		# When found: continue until edge section is found
		edge_found=0
		for line in mpx_lines[line_count:]:
			# If #EDGES not found, continue
			if edge_found==0 and ("#EDGES" not in line and "# EDGES" not in line):
				line_count=line_count+1
				continue
			# Edges found- move to next section
			elif edge_found==0:
				edge_found=1
				continue
			
			# When found: start parsing edges until new section found
			if line.strip()!="":
				# Continue if section start
				if line[0]=="#":
					continue
				# Ignore comment lines
				if line[0:2]=="--":
					continue
				# Format for simple multiplex: nodeSrc nodeDst layer
				tokens=line.split(",")

				# If multiplex network type:
				if net_type==0:
					# Save node and layer labels into dictionary for later retrieval.
					# 	Searching through a list would be VERY costly.
					ns_ind=-1
					nd_ind=-1
					l_ind=-1
					# For nodeSrc:
					if tokens[0] not in actor_dict:
						actor_dict[tokens[0]]=actor_index
						ns_ind=actor_index
						actor_index=actor_index+1
					else:
						ns_ind=actor_dict[tokens[0]]
					# For nodeDst:
					if tokens[1] not in actor_dict:
						actor_dict[tokens[1]]=actor_index
						nd_ind=actor_index
						actor_index=actor_index+1
					else:
						nd_ind=actor_dict[tokens[1]]
					# For layer:
					if tokens[2] not in layer_dict:
						layer_dict[tokens[2]]=layer_index
						l_ind=layer_index
						layer_index=layer_index+1
					else:
						l_ind=layer_dict[tokens[2]]

					# Write found edge into edgefile. Assign weight=1
					# Format: layer nodeSrc nodeDst weight
					edge_str=str(l_ind)+" "+str(ns_ind)+" "+str(nd_ind)+" 1\n"
					wf_edge.write(edge_str)
				# else if multilayer network type:
				elif net_type==1:
					# Save node and layer labels into dictionary for later retrieval.
					# 	Searching through a list would be VERY costly.
					ns_ind=-1
					nd_ind=-1
					ls_ind=-1
					ld_ind=-1
					# For nodeSrc:
					if tokens[0] not in actor_dict:
						actor_dict[tokens[0]]=actor_index
						ns_ind=actor_index
						actor_index=actor_index+1
					else:
						ns_ind=actor_dict[tokens[0]]
					# For nodeDst:
					if tokens[2] not in actor_dict:
						actor_dict[tokens[2]]=actor_index
						nd_ind=actor_index
						actor_index=actor_index+1
					else:
						nd_ind=actor_dict[tokens[2]]
					# For layerSrc:
					if tokens[1] not in layer_dict:
						layer_dict[tokens[1]]=layer_index
						ls_ind=layer_index
						layer_index=layer_index+1
					else:
						ls_ind=layer_dict[tokens[1]]
					# For layerDst:
					if tokens[3] not in layer_dict:
						layer_dict[tokens[3]]=layer_index
						ld_ind=layer_index
						layer_index=layer_index+1
					else:
						ld_ind=layer_dict[tokens[3]]

					# Write found edge into edgefile. Assign weight=1
					# Format: nodeSrc layerSrc nodeDst layerDst weight
					edge_str=str(ns_ind)+" "+str(ls_ind)+" "+str(nd_ind)+" "+str(ld_ind)+" 1\n"
					wf_edge.write(edge_str)
			line_count=line_count+1


	# Finally, write the node and layer files from the dictionaries
	wf_node.write("nodeID nodeLabel\n") # Header
	for actor_k in actor_dict.keys():
		# Format: nodeID nodeLabel
		node_str=str(actor_dict[actor_k])+" "+actor_k+"\n"
		wf_node.write(node_str)
	wf_node.write("\n")

	wf_layer.write("layerID layerLabel\n") # Header
	for layer_k in layer_dict.keys():
		# Format layerID layerLabel
		layer_str=str(layer_dict[layer_k])+" "+layer_k
		wf_layer.write(layer_str)
	wf_layer.write("\n")

	# Close files
	rf.close()
	wf_node.close()
	wf_edge.close()
	wf_layer.close()

# Quick fix for MuxViz, set node indices starting with 1.
def rewrite_multiplex_plus_one(file):
	rf=open(file,"r")
	lines=rf.readlines()
	rf.close()
	wf=open(file,"w")
	for ln in lines:
		tokens=ln.split(" ")
		w_str=""+str(1+int(tokens[0]))+" "+tokens[1]+" "+str(1+int(tokens[2]))+" "+tokens[3]+" "+tokens[4]
		wf.write(w_str)
	wf.close()

# Write config file for MuxViz.
def write_muxviz_config(filename_nodes,filename_edges,filename_layers,write_config):
	wf=open(write_config,"w")
	wf.write(""+filename_edges+";"+filename_layers+";"+filename_nodes+"\n")
	wf.close()

def main():

	for filename in glob.glob("../data/synth/*_multiplex.edges"):
		# Fix filename +1s
		rewrite_multiplex_plus_one(filename)
		

	# # Synth conversion to all formats. Open all files in synth path
	# for filename in glob.glob("../data/synth/*.edges"):
	# 	# Extract base of filename
	# 	filename_base=(filename.split(".edges"))[0]

	# 	# First, convert to multinet simple
	# 	filename_mpx=filename_base+".mpx"
	# 	multiplex_edge_to_multinet_simple(
	# 		filename,
	# 		filename_mpx
	# 	)

	# 	filename_nodes=filename_base+"_nodes.txt"
	# 	filename_layers=filename_base+"_layers.txt"
	# 	filename_edges=filename_base+"_multiplex.edges"
	# 	# Then convert to multiplex triple
	# 	multinet_simple_to_multiplex_edge(
	# 		filename_mpx,
	# 		filename_nodes,
	# 		filename_edges,
	# 		filename_layers
	# 	)
	# 	multiplex_edge_to_multilayer_edge(
	# 		filename,
	# 		filename_edges
	# 	)

	# 	filename_config=filename_base+".config"
	# 	# ...and generate MuxViz config file
	# 	write_muxviz_config(
	# 		filename_nodes,
	# 		filename_edges,
	# 		filename_layers,
	# 		filename_config
	# 	)

	# 	filename_netmem=filename_base+"_netmem.edges"
	# 	# And convert to netmem multiplex simple
	# 	multiplex_edge_to_netmem_multiplex(
	# 		filename,
	# 		filename_netmem
	# 	)


	## OLD CONVERSIONS
	#
	# multiplex_edge_to_multilayer_edge(
	# 	"../data/london-transport/london_transport_multiplex.edges",
	# 	"../data/london-transport/london_transport_multilayer.edges"
	# )
	# multiplex_edge_to_multilayer_edge(
	# 	"../data/euair-transport/EUAirTransportation_multiplex.edges",
	# 	"../data/euair-transport/EUAirTransportation_multilayer.edges"
	# )
	# multiplex_edge_to_multilayer_edge(
	# 	"../data/cs-aarhus/CS-Aarhus_multiplex.edges",
	# 	"../data/cs-aarhus/CS-Aarhus_multilayer.edges"
	# )
	# multiplex_edge_to_multinet_simple(
	# 	"../data/euair-transport/EUAirTransportation_multiplex.edges",
	# 	"../data/euair-transport/euair.mpx"
	# )
	# multiplex_edge_to_multinet_simple(
	# 	"../data/london-transport/london_transport_multiplex.edges",
	# 	"../data/london-transport/london.mpx"
	# )
	# multiplex_edge_to_multinet_full(
	# 	"../data/london-transport/london_transport_nodes.txt",
	# 	"../data/london-transport/london_transport_multiplex.edges",
	# 	"../data/london-transport/london_transport_layers.txt",
	# 	"../data/london-transport/london-full.mpx"
	# )
	# multiplex_edge_to_multinet_full(
	# 	"../data/euair-transport/EUAirTransportation_nodes.txt",
	# 	"../data/euair-transport/EUAirTransportation_multiplex.edges",
	# 	"../data/euair-transport/EUAirTransportation_layers.txt",
	# 	"../data/euair-transport/euair-full.mpx"
	# )
	# multinet_simple_to_multiplex_edge(
	# 	"../data/ff-tw/fftw.mpx",
	# 	"../data/ff-tw/fftw_nodes.txt",
	# 	"../data/ff-tw/fftw_multiplex.edges",
	# 	"../data/ff-tw/fftw_layers.txt"
	# )
	# multinet_simple_to_multiplex_edge(
	# 	"../data/friendfeed/friendfeed.mpx",
	# 	"../data/friendfeed/friendfeed_nodes.txt",
	# 	"../data/friendfeed/friendfeed_multiplex.edges",
	# 	"../data/friendfeed/friendfeed_layers.txt"
	# )
	# multinet_simple_to_multiplex_edge(
	# 	"../data/ff-tw/fftw.mpx",
	# 	"../data/ff-tw/fftw_nodes.txt",
	# 	"../data/ff-tw/fftw_multiplex.edges",
	# 	"../data/ff-tw/fftw_layers.txt"
	# )
	# multiplex_edge_to_multilayer_edge(
	# 	"../data/ff-tw/fftw_multiplex.edges",
	# 	"../data/ff-tw/fftw_multilayer.edges"
	# )
	# multiplex_edge_to_multilayer_edge(
	# 	"../data/friendfeed/friendfeed_multiplex.edges",
	# 	"../data/friendfeed/friendfeed_multilayer.edges"
	# )
	# multiplex_edge_to_multinet_simple(
	#  	"../data/friendfeed/friendfeed_multiplex.edges",
	#  	"../data/friendfeed/ff_simple.mpx"
	# )
	# multiplex_edge_to_multilayer_edge(
	# 	"../data/florentine/Padgett-Florentine-Families_multiplex.edges",
	# 	"../data/florentine/Padgett-Florentine-Families_multilayer.edges"
	# )
	# multiplex_edge_to_netmem_multiplex(
	# 	"../data/london-transport/london_transport_multiplex.edges",
	# 	"../data/london-transport/london_transport_netmem.edges"
	# )
	# multiplex_edge_to_netmem_multiplex(
	# 	"../data/euair-transport/EUAirTransportation_multiplex.edges",
	# 	"../data/euair-transport/EUAirTransportation_netmem.edges"
	# )
	# multiplex_edge_to_netmem_multiplex(
	# 	"../data/cs-aarhus/CS-Aarhus_multiplex.edges",
	# 	"../data/cs-aarhus/CS-Aarhus_netmem.edges"
	# )
	# multiplex_edge_to_netmem_multiplex(
	# 	"../data/friendfeed/friendfeed_multiplex.edges",
	# 	"../data/friendfeed/friendfeed_netmem.edges"
	# )
	# multiplex_edge_to_netmem_multiplex(
	# 	"../data/ff-tw/fftw_multiplex.edges",
	# 	"../data/ff-tw/fftw_netmem.edges"
	# )
	



# Python stuff
if __name__ == "__main__":
	main()