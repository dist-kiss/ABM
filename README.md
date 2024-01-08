# Agent Based Model Dist Kiss


### Brief description of contents
The model can be found in ```model_code/distkiss_model.py```. Some functions used in the model are outsourced into other files, these are ```model_code/graph_helpers.py```, ```model_code/movement.py```, ```model_code/spatial_output_creator.py```. There are several files to run the model with different parameter sets and configurations called ```run_[...].py```.
An animation of the model can be created by runnning ```model_code/graph_helpers.py```. To perform a sensitivity analysis use the script ```model_code/run_sensitivity.py```. 

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
│   │   run_sensitivity.py (script to run model & execute sensitivity analysis)
│   │   run_single_model_run.py (script to run a single model run)
│   │   run_study_experiments.py (script to reproduce experiments from the research paper)
│   │   run_with_optimal_parameters.py (script to run the model with calibrated parameter set)
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


### BRIEF MODEL DESCRIPTION:
This model allows to evaluate the change in pedestrian movement flows due to streetscape interventions such as one way streets for pedestrians during a pandemic such as the COVID-19 pandemic. The theory of the model is that pedestrians do not always comply with these types of interventions, i.e. they violate the rules in certain situations. The model aims at modelling the agent’s decision whether or not to comply with interventions at street intersections and the resulting city-wide movement patterns and crowdedness of streets.