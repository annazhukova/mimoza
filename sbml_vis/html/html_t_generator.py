import io
import logging
import os

from jinja2 import Environment, PackageLoader

from sbml_vis.mimoza_path import PROGRESS_ICON, LEAFLET_LABEL_CSS, LEAFLET_CSS, LEAFLET_LABEL_JS, LEAFLET_JS, \
    MIMOZA_GEOJSON_JS, MIMOZA_POPUP_JS, MIMOZA_JS
from sbml_vis.converter.tlp2geojson import DEFAULT_LAYER2MASK

VISUALIZATION = 'Visualization'

__author__ = 'anna'


def get_download_tab(map_id, groups_sbml_url, archive_url):
    env = Environment(loader=PackageLoader('sbml_vis.html', 'templates'))
    template = env.get_template('download_tab.html')
    return template.render(map_id=map_id, groups_sbml_url=groups_sbml_url, archive_url=archive_url)


def get_vis_tab(non_empty, model_name, model_id, c_id2name, json_files, c_id2json_vars, map_id, c_id2out_c_id,
                hidden_c_ids, c_id_hidden_ubs, layer2mask=DEFAULT_LAYER2MASK, info=''):
    env = Environment(loader=PackageLoader('sbml_vis.html', 'templates'))
    template = env.get_template('map_tab.html')
    c_id2json_vars = '{%s}' % ", ".join(
        ("'%s':[%s]" % (c_id, ", ".join(json_vars)) for (c_id, json_vars) in c_id2json_vars.items()))
    logging.info('Rendering the model...')
    model_name = model_name if model_name else ''
    model_id = model_id if model_id else ''
    map_id = map_id if map_id else ''
    layer2mask = '[%s]' % ", ".join(("['%s', %d]" % (l_id, m) for (l_id, m) in layer2mask.items()))
    return template.render(non_empty=non_empty,
                           model_name=model_name,
                           model_id=model_id,
                           json_files=json_files,
                           c_id2json_vars=c_id2json_vars,
                           map_id=map_id,
                           c_id2out_c_id=c_id2out_c_id,
                           comp_c_id2name=sorted(c_id2name.items(), key=lambda it: it[1])
                           if len(c_id2name) > 1 else None,
                           c_id2name=c_id2name, layer2mask=layer2mask,
                           hidden_c_ids=hidden_c_ids, c_id_hidden_ubs=c_id_hidden_ubs, info=info, invisible_layers=[])


def create_html(non_empty, model_name, model_id, c_id2name,
                directory, json_files, c_id2json_vars, map_id, c_id2out_c_id, hidden_c_ids, c_id_hidden_ubs,
                layer2mask=DEFAULT_LAYER2MASK, tab2html=None, title='', h1='', invisible_layers=None):

    if not invisible_layers:
        invisible_layers = []

    model_name = model_name if model_name else ''
    model_id = model_id if model_id else ''
    map_id = map_id if map_id else ''
    if not title:
        title = 'Visualization of <a href="http://www.ebi.ac.uk/biomodels-main/%s">%s</a>' % (model_id, model_name)
    if not h1:
        h1 = model_name

    vis_tab = get_vis_tab(non_empty, model_name, model_id, c_id2name, json_files, c_id2json_vars, map_id, c_id2out_c_id,
                          hidden_c_ids, c_id_hidden_ubs, layer2mask=DEFAULT_LAYER2MASK, info='')
    tab2html[VISUALIZATION] = vis_tab, "icon-happy"

    # Make sure that visualisation goes first
    tab2html = sorted(tab2html.items(), key=lambda it: (2, it[0]) if it[0] != VISUALIZATION else (1, it[0]))

    env = Environment(loader=PackageLoader('sbml_vis.html', 'templates'))
    template = env.get_template('tabbed_page.html')

    page = template.render(css_list=[LEAFLET_LABEL_CSS, LEAFLET_CSS],
                           js_list=[LEAFLET_JS, LEAFLET_LABEL_JS, MIMOZA_JS, MIMOZA_POPUP_JS, MIMOZA_GEOJSON_JS],
                           h1=h1, title=title, tab2html=tab2html)
    with io.open(os.path.join(directory, 'comp.html'), 'w+', encoding='utf-8') as f:
        f.write(page)

    template = env.get_template('index.html')
    page = template.render()
    with open(os.path.join(directory, 'index.html'), 'w+') as f:
        f.write(page)

    logging.info('Rendering the mini model...')
    template = env.get_template('comp_min.html')
    page = template.render(model_name=model_name, json_files=json_files, c_id2json_vars=c_id2json_vars,
                           map_id=map_id, c_id2out_c_id=c_id2out_c_id, c_id2name=c_id2name,
                           layer2mask=layer2mask, c_id_hidden_ubs=c_id_hidden_ubs,
                           hidden_c_ids=hidden_c_ids, invisible_layers=invisible_layers)
    with io.open(os.path.join(directory, 'comp_min.html'), 'w+', encoding='utf-8') as f:
        f.write(page)


def generate_model_html(title, h1, text, expl, more_expl, model_id, sbml, gen_sbml, sbgn, gen_sbgn,
                        m_dir_id, progress_icon, action):
    env = Environment(loader=PackageLoader('sbml_vis.html', 'templates'))
    template = env.get_template('action.html')
    return template.render(title=title, h1=h1, text=text, expl=expl, more_expl=more_expl, model_id=model_id,
                           sbml=sbml, gen_sbml=gen_sbml, sbgn=sbgn, gen_sbgn=gen_sbgn,
                           m_dir_id=m_dir_id, progress_icon=progress_icon, action=action)


def generate_uploaded_sbml_html(m_name, m_id, m_url, sbml, gen_sbml, sbgn, gen_sbgn, m_dir_id, progress_icon):
    return generate_model_html(title="%s Uploaded" % (m_name if m_name else m_id), h1="Uploaded, time to generalize!",
                               text='',
                               expl='Now let\'s generalize it: To start the generalization press the button below.',
                               more_expl='''<br>When the generalization is done,
                               it will become available at <a href="%s">%s</a>.
                               <br>It might take some time (up to an hour for genome-scale models),
                               so, please, be patient and do not lose hope :)'''% (m_url, m_url),
                               model_id=m_id, sbml=sbml, gen_sbml=gen_sbml, sbgn=sbgn, gen_sbgn=gen_sbgn,
                               m_dir_id=m_dir_id, progress_icon=progress_icon, action='generalize.py')


def generate_uploaded_generalized_sbml_html(m_name, m_id, m_url, sbml, gen_sbml, sbgn, gen_sbgn, m_dir_id, progress_icon):
    return generate_model_html(title="%s Uploaded" % (m_name if m_name else m_id), h1="Uploaded, time to visualize!",
                               text='', expl='''Your model seems to be already generalized.
                               Now let\'s visualize it: To start the visualization press the button below.<br>
                               <i>(If your model contains
                               <a href="http://sbml.org/Documents/Specifications/SBML_Level_3/Packages/Layout_%28layout%29"
                               target="_blank">SBML layout</a> information,
                               it will be used during the visualization.)</i>''',
                               more_expl='''<br>When the visualization is done,
                               it will become available at <a href="%s">%s</a>.''' % (m_url, m_url),
                               model_id=m_id, sbml=sbml, gen_sbml=gen_sbml, sbgn=sbgn, gen_sbgn=gen_sbgn,
                               m_dir_id=m_dir_id, progress_icon=progress_icon, action='visualise.py')


def generate_generalization_finished_html(m_name, m_id, m_url, sbml, gen_sbml, sbgn, gen_sbgn, m_dir_id, progress_icon):
    return generate_model_html(title="%s Generalized" % (m_name if m_name else m_id),
                               h1="Generalized, time to visualize!",
                               text='', expl='''Your model is successfully generalized.
                               Now let\'s visualize it: To start the visualization press the button below.''',
                               more_expl='''<br>When the visualization is done,
                               it will become available at <a href="%s">%s</a>.''' % (m_url, m_url),
                               model_id=m_id, sbml=sbml, gen_sbml=gen_sbml, sbgn=sbgn, gen_sbgn=gen_sbgn,
                               m_dir_id=m_dir_id, progress_icon=progress_icon, action='visualise.py')


def create_thanks_for_uploading_html(m_id, m_name, directory_prefix, m_dir_id, url, url_end,
                                     generate_html=generate_uploaded_sbml_html, groups_suffix='_with_groups'):
    directory = os.path.join(directory_prefix, m_dir_id)
    m_url = '%s/%s/%s' % (url, m_dir_id, url_end)
    sbml = os.path.join(directory, '%s%s.xml' % (m_id, groups_suffix))
    gen_sbml = os.path.join(directory, '%s_generalized.xml' % m_id)
    sbgn = os.path.join(directory, '%s_initial_model.sbgn' % m_id)
    gen_sbgn = os.path.join(directory, '%s_generalized.sbgn' % m_id)

    with open(os.path.join(directory, 'index.html'), 'w+') as f:
        page = generate_html(m_name, m_id, m_url, sbml, gen_sbml, sbgn, gen_sbgn, m_dir_id, PROGRESS_ICON)
        f.write(page)

