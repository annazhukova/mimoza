# Mimoza

*Mimoza* is a a Python library for metabolic model visualization and navigation that allows you
to explore your metabolic models in a semantically zoomable manner.

*Mimoza* combines the [model generalization method](http://metamogen.gforge.inria.fr)
with the zooming user interface ([ZUI](http://en.wikipedia.org/wiki/Zooming_user_interface))
paradigm and allows a human expert to explore metabolic network models in a semantically zoomable manner.

*Mimoza* takes a metabolic model in [SBML](http://sbml.org) format, generalizes it to detect similar metabolites
and similar reactions, and automatically creates a 3-level zoomable map:

1. the most detailed view represents the initial network with the generalization-based layout
  (similar metabolites and reactions are placed next to each other).
2. the intermediate view shows the generalized versions of reactions and metabolites in each compartment;
3. the general view represents the compartments and the transport reactions between them.

*Mimoza* highlights the general model structure and the divergences from it, such as alternative paths or missing reactions,
and allows a user to analyse it in a top-down manner.

The network map can be browsed online or downloaded as a [COMBINE archive](http://co.mbine.org/documents/archive>), containing:

* all the files needed for offline browsing;
* SBML files with the groups and layout extensions, representing the initial and generalized versions of your model
  and their layout;
* [SBGN](http://www.sbgn.org) representation of your model.


## Article

Zhukova, A., Sherman, D. J. (2015) **Mimoza: Web-Based Semantic Zooming and Navigation in Metabolic Networks** *BMC Systems Biology*, **9:**10
[doi:10.1186/s12918-015-0151-5](http://identifiers.org/doi/10.1186/s12918-015-0151-5)


## Dependencies

*Mimoza* uses [libSBML](http://sbml.org/Software/libSBML) library for python with the groups and layout extensions.
To install it:

```bash
sudo pip3 install python-libsbml-experimental
```

*Mimoza* uses [Model Generalization](https://github.com/annazhukova/mod_gen) library for python 
to produce generalized views of the model and [Mod_SBML](https://github.com/annazhukova/mod_sbml) library.
To install them

```bash
sudo pip3 install mod_sbml
sudo pip3 install sbml_generalization
```

*Mimoza* uses [Tulip 4.4](http://tulip.labri.fr/Documentation/current/tulip-python/html/index.html) library for python to layout metabolic networks.
To install it:

```bash
sudo pip3 install tulip-python
```

*Mimoza* uses [SymPy](http://www.sympy.org), Python bindings for [geojson](https://pypi.python.org/pypi/geojson),
and [Jinja2] (http://jinja.pocoo.org):

```bash
sudo pip3 install sympy
sudo pip3 install geojson
sudo pip3 install Jinja2
```

If you want to have export of your maps in [SBGN PD](http://www.sbgn.org), 
install [libSBGN bindings for Python](https://github.com/matthiaskoenig/libsbgn-python):
  
```bash
sudo pip3 install libsbgnpy
```

*Mimoza* also uses [Leaflet](http://leafletjs.com/), [the ChEBI Ontology](http://www.ebi.ac.uk/chebi/),
and [the Gene Ontology](http://geneontology.org), but you do not need to install them.

*Mimoza* was developed using [PyCharm](http://www.jetbrains.com/pycharm).


## Installing Mimoza

From the directory where you have extracted this archive, execute:

```bash
python3 setup.py
```

Do not forget to install the dependencies (see above).


## Running Mimoza

Execute:
  
```bash
python3 ./main.py --model path_to_your_model.xml --verbose
```

This will produce a [COMBINE archive](http://co.mbine.org/documents/archive), containing:

* the visualized model (You can see the result in your browser (index.html file inside the COMBINE archive));
* SBML files with the groups and layout extensions, representing the initial and generalized versions of your model
  and their layout;
* SBGN representation of your model (if the SBGN bindings are installed, see Dependencies).
