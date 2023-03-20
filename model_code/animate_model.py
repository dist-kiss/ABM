import distkiss_abm
import agentpy as ap
import numpy as np
import time
import matplotlib.pyplot as plt 

#  ------ ANIMATION ------------------------
anim_parameters = {
    'agents': 50, # number of agents 
    'steps': 720, # number of timesteps (model stops if all agents reached their destination before the amount of steps is reached) 
    'duration': 5,
    'streets_path': "../input_data/quakenbrueck_street_width.gpkg",
    # Model weights
    'constant_weight_mean': 0.3424823265591154,
    'constant_weight_sd': 0.4042530941646003,
    'rtd_weight_mean': 4.062769564671944, 
    'rtd_weight_sd': 1.7983272569373019,
    'ows_weight_mean': -1.686987748677264, 
    'ows_weight_sd': 0.453969999609177449,
    'walking_speed_mean': 1.25,
    'walking_speed_std': 0.21,
    # Density not used as weight so far.
    'weight_density': 0,
    'seed': 43,
    # Choose value from ['no_interventions', 'simple_compliance', 'complex_compliance'] for parameter to decide which scenario to run:
    # Scenario 1: 'no_interventions' = Agents behave like there are no measures 
    # Scenario 2: 'simple_compliance' = Agents comply with every measure
    # Scenario 3: 'complex_compliance' = Agents use complex decision making for compliance with measures
    'scenario': 'complex_compliance',
    # Choose when to record non compliance probability (basically choose definition of non compliance); Default is True:
    # False = Non compliance is only where agent initially wanted to walk into forbidden one way street
    # True = Additionally in situations, in which agent keeps its route doing a second evalutation after initally 
    #       wanting to (randomly) reroute into ows.
    'record_second_opinion_ncps': True,
    # Whether agents can reroute from inital path, by default True. Only turn of if agents shall be restricted to inital path!
    'rerouting_allowed': True,
    # Whether to assign new origin & destinations to agents after having reached their destination.
    'assign_new_destinations': True,
    # Whether only new destinations shall be assigned and previous destination is used as origin
    'reuse_previous_dest_as_orig': False,
    'epoch_time': int(time.time()),
    'origin_destination_pairs': False,
    # 'origin_destination_pairs': tuple([tuple([27,9]),tuple([32,27]),tuple([0,39])]),
    # Whether positions, edges and destination should be saved as gpkg files:
    'positions': False,
    'edges' : False,
    'destination_log': False,
    'compliance_nodes': False,
    'max_densities': False,
    # Add logs for debugging
    'logging': False,
}

from IPython.display import HTML

def animation_plot_single(m, ax):
    ndim = 2
    ax.set_title(f"Dist-KISS Model {ndim}D t={m.t}")
    pos = m.space.positions.values()
    pos = np.array(list(pos)).T  # Transform
    lines = m.edges.translate(xoff=-m.x_min, yoff=-m.y_min, zoff=0.0)
    lines.plot(ax=ax,color = 'green', label = 'network', zorder=1)
    ax.scatter(*pos, s=2, c='black', zorder=2)
    ax.set_xlim(0, m.width)
    ax.set_ylim(0, m.height)
    ax.set_axis_off()

def animation_plot(m, p):
    projection = None
    fig = plt.figure(figsize=(7,7))
    ax = fig.add_subplot(111, projection=projection)
    animation = ap.animate(m(p), fig, ax, animation_plot_single)    
    with open("../animation_output/Model_%d_Animation.html" % m(p).p.epoch_time, "w") as file:
        file.write(animation.to_jshtml(fps=10))
    # return HTML(animation.to_jshtml(fps=20))
import matplotlib
matplotlib.rcParams['animation.embed_limit'] = 2**128

# TO PRODUCE ANIMATION UMCOMMENT THE FOLLOWING LINE:
animation_plot(distkiss_abm.DistanceKeepingModel, anim_parameters)
print("Script completed.")