# Agent Based Model Dist Kiss


### Brief description of contents
The model can be found in ```model_code/distkiss_model.py```. Some functions used in the model are outsourced into other files, these are ```model_code/graph_helpers.py```, ```model_code/movement.py```, ```model_code/spatial_output_creator.py```. There are several files to run the model with different parameter sets and configurations called ```run_[...].py```.
An animation of the model can be created by runnning ```model_code/animate_model.py```. To perform a sensitivity analysis use the script ```model_code/run_sensitivity_analysis.py```. 

All model runs should be executed from within the repository root folder, running `python model_code/run_mymodel.py`.
A cross_platform conda environment is included and shall be used to set up the python environment. To reproduce results form the experiments in the research paper, follow these steps:
1. Run model_code/run_stuy_experiments.py (will take some time, you can adapt the amount of cores to increase parallelization)
2. Run postprocessing/01_map_mean_density_per_street.py
3. Run postprocessing/02_diff_stats_densities.py
4. Run postprocessing/03_mean_densities_by_scenario.py
5. Run postprocessing/reproduce_violin_plots.py (can also be run without running the aforementioned script, for violinplots only)

### File structure of the repository
```
project
│   .gitignore    
│   cross_platfrom_environment.yml (conda environment, preferred option)
│   osx_platform_package_specific.yml (conda environment mac silicon specific, tested with MBPro M2 Pro)
│   README.md
│
└───animation_output
│   │   example_animation.html
│   
└───input_data
│   │   quakenbrueck_street_width_no_ows.gpkg
│   │   quakenbrueck_street_width_4_ows.gpkg
│   │   quakenbrueck_street_width_8_ows.gpkg (currently used as default input file)
│   │   quakenbrueck_street_width_10_ows.gpkg
│
└───model_code
│   │   animate_model.py (creates animation of model)
│   │   distkiss_abm.py (the actual model code)
│   │   graph_helpers.py (helper functions for model)
│   │   movement.py (helper functions for model)
│   │   run_custom_experiment.py (script to run your custom AgentPy experiments with the model)
│   │   run_single_model_run.py (script to run a single model run)
│   │   run_study_experiments.py (script to reproduce experiments from the research paper)
│   │   run_with_optimal_parameters.py (script to run the model with calibrated parameter set)
│   │   run_sensitivity_analysis.py (script to run model & execute sensitivity analysis)
│   │   load_sensitivity_analysis.py (script to load model output created with "run_sensitivity_analysis.py" & execute sensitivity analysis)
│   │   sensitivity_plots.py (helper unctions for sensitivity result visualizations)
│   │   spatial_output_creator.py (helper functions for saving model outputs)
│
└───postprocessing (allows reproduction of study results and plots)
│   │   01_map_mean_density_per_street.py
│   │   02_diff_stats_densities.py
│   │   03_mean_densities_by_scenario.py
│   │   reproduce_violin_plots.py
│
└───qgis_styles
    │   compliance_location_style.qml
    │   edges_style_conference.qml
    │   ows_style_conference.qml
    │   points_style_conference.qlr
    │   points_style_conference.qml


```

### Running the model

There are several files that can be used to run the model for different purposes. Here a brief overview of what they are made for is given:

1. **run_single_model_run.py** - This is the simplest of all version. The model is run for the scenario of "complex" compliance behavior (agents dynamically decide to comply or not to comply and to reroute) with a default configuration of 200 agents and 720 timesteps (1 hour time equivalent). All outputs are disabled in the parameter set. The model will run, but produce an empty output folder. Output parameters can be set to true, to generate outputs. 

2. **run_with_optimal_parameters.py** - Similar to the **run_single_model_run** but with 2000 agents and model outputs are activated. These are: (1) positions of all agents for all timesteps (2) edges, with pedestrian counts, for all timesteps, (3) compliance nodes and (4) edges with maximum density over all timesteps are created as outputs.

3. **animate_model.py** - This file creates a html animation as output. The animation shows the street network with agents and their positions as dots over time.

4. **run_custom_experiment.py** - This is version runs an experiment, where the scenario is varied, between _simple compliance_ (all agents comply with all interventions), _complex compliance_ (agents dynamically decide to comply or not to comply) and _no interventions_ (there are no interventions on the streets). The model is run 10 times (iterations) for each scenario with different model seeds. By default (1) edges, with pedestrian counts, for all timesteps, (2) compliance nodes and (3) edges with maximum density over all timesteps are created as outputs. Additionally, the following outputs are generated in reporters.csv:
```
mean normalized oberserved detour, std of normalized oberserved detour, variance of normalized oberserved detour, mean non-compliance probability, std of non-compliance probability, variance of non-compliance probability, mean compliance probability, std of compliance probability, number of non-compliances, number of compliances, number of no-route-changes, number of random-reroutings, Array of shortest path lengths, Array of total path legngths, Array of normalized observed detours, Array of non-compliance probabilities, Array of compliance probabilities
```

5. **run_study_experiments.py** - This version runs all experiment that were run for the corresponding research paper. First an experiment, where the scenario is varied, between _simple compliance_ (all agents comply with all interventions), _complex compliance_ (agents dynamically decide to comply or not to comply) and _no interventions_ (there are no interventions on the streets) is run. The model is run 10 times (iterations) for each scenario with different model seeds. Next four consecutive experiments are run, with different one way street (ows) configurations (1. no ows, four ows, eight ows, ten ows). In each of these ecperiments, the number of agents is varied between 2000, 4000 and 10000 agents. The scenario is always _complex compliance_ (agents dynamically decide to comply or not to comply). In each experiment the model is run 10 times (iterations) for each configuratuion, reuslting in 30 model runs per Experiment.

By default (1) edges, with pedestrian counts, for all timesteps and (2) edges with maximum density over all timesteps are created as outputs. Additionally, the following outputs are generated in reporters.csv:
```
mean normalized oberserved detour, std of normalized oberserved detour, variance of normalized oberserved detour, mean non-compliance probability, std of non-compliance probability, variance of non-compliance probability, mean compliance probability, std of compliance probability, number of non-compliances, number of compliances, number of no-route-changes, number of random-reroutings, Array of shortest path lengths, Array of total path legngths, Array of normalized observed detours, Array of non-compliance probabilities, Array of compliance probabilities
```

6. **run_sensitivity_analysis.py** - This script runs a sensitivity analysis for the model. Change the parameter dictionary "sa_parameters" to create different samples and use these samples to run the model. With the so created model-outputs, later the sensitivity analysis is performed. Unlike in other model runs, weights for the compliance function and walking speed are drawn from this range:<br/><br/>**range(mean of the parameter - (2 * SD of the parameter), mean of the parameter + (2 * SD of the parameter))**.<br/><br/> Values for the means and SD's have to be gathered e.g. via study, literature.
This is done to get an evenly distributed parameter space for the later sample creation. The model is run multiple times systematically varying the parameters by inputing a different sample. Sample size "N" can be adjusted. This results in a better convergenece of the Sobol' Sequence which improves the sample data quality, but also increasing the runtime significantly. The default is 1024 for this model. Runtime varies heavily depending on the specifications of your machine, so an estimation of the runtime can't be given.
After calculating the Sobol' Indices you can plot the results with the functions provided in "sensitivity_plots.py".
For further information on this topic, please consider:
    - [SALib](https://salib.readthedocs.io/en/latest/index.html)
    - [Agentpy](https://agentpy.readthedocs.io/en/latest/reference_data.html?highlight=sobol)

6. **load_sensitivity_analysis.py** - This script loads an experiment performed with "run_sensitivity_anaylsis.py" and calculates the Sobol' Indices on this data. After this calculation you can plot the results with the functions provided in "sensitivity_plots.py".



### BRIEF MODEL DESCRIPTION:
This model allows to evaluate the change in pedestrian movement flows due to streetscape interventions such as one way streets for pedestrians during a pandemic such as the COVID-19 pandemic. The theory of the model is that pedestrians do not always comply with these types of interventions, i.e. they violate the rules in certain situations. The model aims at modelling the agent’s decision whether or not to comply with interventions at street intersections and the resulting city-wide movement patterns and crowdedness of streets.