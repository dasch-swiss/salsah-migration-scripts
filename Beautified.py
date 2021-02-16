import copy
from pprint import pprint
import requests
import json
from typing import List, Set, Dict, Tuple, Optional

import time


class Converter:

    def __init__(self):
        self.serverpath: str = "https://www.salsah.org"
        # self.serverpath: str = "http://salsahv1.unil.ch"
        self.selection_mapping: Dict[str, str] = {}
        self.selection_node_mapping: Dict[str, str] = {}
        self.hlist_node_mapping: Dict[str, str] = {}
        self.hlist_mapping: Dict[str, str] = {}

        # Retrieving the necessary informations from Webpages.
        self.salsahJson = requests.get(f'{self.serverpath}/api/projects').json()
        self.r = requests.get(
            'https://raw.githubusercontent.com/dhlab-basel/dasch-ark-resolver-data/master/data/shortcodes.csv')
        self.salsahVocabularies = requests.get(f'{self.serverpath}/api/vocabularies').json()

        self.name_list = self.name_mapper()
        self.name_list.update({"webern": "webern"})

    # ==================================================================================================================
    # Function that fills the shortname as well as the longname into the empty ontology. Uses https://www.salsah.org/api/projects for that
    def fillShortLongName(self, project):
        tmpOnto["project"]["shortname"] = project["shortname"]
        tmpOnto["project"]["longname"] = project["longname"]

    # ==================================================================================================================
    # Fill in the project id's to the corrisponging projects. Using https://raw.githubusercontent.com/dhlab-basel/dasch-ark-resolver-data/master/data/shortcodes.csv
    def fillId(self, project):
        lines = salsahJson.r.text.split('\n')
        for line in lines:
            parts = line.split(',')
            if len(parts) > 1 and parts[1] == project["shortname"]:
                tmpOnto["project"]["shortcode"] = parts[0]
                # print('Found Knora project shortcode "{}" for "{}"!'.format(shortcode, parts[1]))

    # ==================================================================================================================
    # Fill the description - if present - into the empty ontology
    def fillDesc(self, project):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["description"] and vocabularies["shortname"].lower() == project["shortname"].lower():
                tmpOnto["project"]["descriptions"] = vocabularies["description"]

    # ==================================================================================================================
    # Fill in the vocabulary name and label
    def fillVocName(self, projects):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["project_id"] == projects["id"]:
                tmpOnto["project"]["ontologies"][0]["name"] = vocabularies["shortname"]
                tmpOnto["project"]["ontologies"][0]["label"] = vocabularies["longname"]

    # ==================================================================================================================
    # Function responsible to get the keywords of the corresponding project
    def fetchKeywords(self, project):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["project_id"] == projects["id"]:

                req = requests.get(f'{self.serverpath}/api/projects/{vocabularies["shortname"]}?lang=all')

                result = req.json()
                if 'project_info' in result.keys():
                    project_info = result['project_info']
                    if "keywords" in project_info:  # This is needed for DYLAN since not all have a keyword TODO: check if that is correct
                        if project_info['keywords'] is not None:
                            tmpOnto["project"]["keywords"] = list(
                                map(lambda a: a.strip(), project_info['keywords'].split(',')))
                        else:
                            tmpOnto["project"]["keywords"] = [result['project_info']['shortname']]
                else:
                    continue

    # ==================================================================================================================
    # Function that fetches the lists for a correspinding project
    def fetchLists(self, project):
        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if vocabularies["project_id"] == projects["id"]:
                payload: dict = {
                    'vocabulary': vocabularies["shortname"],
                    'lang': 'all'
                }
                req = requests.get(f'{self.serverpath}/api/selections/', params=payload)
                result = req.json()

                selections = result['selections']

                # Let's make an empty list for the lists:
                selections_container = []

                for selection in selections:
                    self.selection_mapping[selection['id']] = selection['name']
                    root = {
                        'name': selection['name'],
                        'labels': dict(map(lambda a: (a['shortname'], a['label']), selection['label']))
                    }
                    if selection.get('description') is not None:
                        root['comments'] = dict(
                            map(lambda a: (a['shortname'], a['description']), selection['description']))
                    payload = {'lang': 'all'}
                    req_nodes = requests.get(f'{self.serverpath}/api/selections/' + selection['id'], params=payload)
                    result_nodes = req_nodes.json()

                    self.selection_node_mapping.update(
                        dict(map(lambda a: (a['id'], a['name']), result_nodes['selection'])))
                    root['nodes'] = list(map(lambda a: {
                        'name': 'S_' + a['id'],
                        'labels': a['label']
                    }, result_nodes['selection']))
                    selections_container.append(root)


                #
                # now we get the hierarchical lists (hlists)
                #
                payload = {
                    'vocabulary': vocabularies["shortname"],
                    'lang': 'all'
                }
                req = requests.get(f'{self.serverpath}/api/hlists', params=payload)
                result = req.json()

                self.hlist_node_mapping.update(dict(map(lambda a: (a['id'], a['name']), result['hlists'])))

                hlists = result['hlists']


                #
                # this is a helper function for easy recursion
                #
                def process_children(children: list) -> list:
                    newnodes = []
                    for node in children:
                        self.hlist_node_mapping[node['id']] = node['name']
                        newnode = {
                            'name': 'H_' + node['id'],
                            'labels': dict(map(lambda a: (a['shortname'], a['label']), node['label']))
                        }
                        if node.get('children') is not None:
                            newnode['nodes'] = process_children(node['children'])
                        newnodes.append(newnode)
                    return newnodes

                for hlist in hlists:
                    root = {
                        'name': hlist['name'],
                        'labels': dict(map(lambda a: (a['shortname'], a['label']), hlist['label']))
                    }
                    self.hlist_mapping[hlist['id']] = hlist['name']
                    if hlist.get('description') is not None:
                        root['comments'] = dict(
                            map(lambda a: (a['shortname'], a['description']), hlist['description']))
                    payload = {'lang': 'all'}
                    req_nodes = requests.get(f'{self.serverpath}/api/hlists/' + hlist['id'], params=payload)
                    result_nodes = req_nodes.json()

                    root['nodes'] = process_children(result_nodes['hlist'])
                    selections_container.append(root)

                tmpOnto["project"]["lists"] = selections_container

    # ==================================================================================================================
    # Function that fetches all the resources that correspond to a vocabulary/ontology
    def fetchResources(self, project):

        superMap = {
            "movie": "MovingImageRepresentation",
            "object": "Resource",
            "image": "StillImageRepresentation"
        }

        for vocabularies in salsahJson.salsahVocabularies["vocabularies"]:
            if project["id"] == vocabularies["project_id"]:
                payload: dict = {
                    'vocabulary': vocabularies["shortname"],
                    'lang': 'all'
                }
                req = requests.get(f'{self.serverpath}/api/resourcetypes/', params=payload)
                resourcetypes = req.json()

                # Here we type in the "name"
                for momResId in resourcetypes["resourcetypes"]:
                    tmpOnto["project"]["ontologies"][0]["resources"].append({
                        "name": momResId["label"][0]["label"],
                        "super": "",
                        "labels": {},
                        "cardinalities": []
                    })
                    # Here we fill in the labels
                    for label in momResId["label"]:
                        tmpOnto["project"]["ontologies"][0]["resources"][-1]["labels"].update(
                            {label["shortname"]: label["label"]})
                    # Here we fill in the cardinalities
                    req = requests.get(f'{self.serverpath}/api/resourcetypes/{momResId["id"]}?lang=all')
                    resType = req.json()
                    resTypeInfo = resType["restype_info"]

                    # if resTypeInfo["class"] not in superMap: #  here we fill in our superMap
                    #     pprint(resTypeInfo["class"])
                    #     exit()

                    tmpOnto["project"]["ontologies"][0]["resources"][-1]["super"] = superMap[
                        resTypeInfo["class"]]  # Fill in the super of the ressource

                    for propertyId in resTypeInfo["properties"]:
                        tmpOnto["project"]["ontologies"][0]["resources"][-1]["cardinalities"].append({
                            "propname": propertyId["name"],
                            # "gui_order": "",  # TODO gui_order not yet implemented by knora.
                            "cardinality": str(propertyId["occurrence"])
                        })
            else:
                continue

    # ==================================================================================================================
    # The following functions are helper functions for "fetchProperties"
    # ==================================================================================================================
    # Function that returns a list of all the resource id's of a project.
    # It gets the json file of the resources of the current project as parameter.
    def res_ids(self, resource_types_json):
        project_resources_ids = []

        for resource_type_id in resource_types_json["resourcetypes"]:
            project_resources_ids.append(resource_type_id["id"])

        return project_resources_ids

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns a List of all the properties id's that are used in that project
    # It gets the json file of the resources of the current project as parameter.
    def prop_ids(self, resource_types_json):
        all_project_properties_ids = []

        for resource_type_id in resource_types_json["resourcetypes"]:
            for property in resource_type_id["properties"]:
                if property["id"] not in all_project_properties_ids and int(property["id"]) != 153:
                    all_project_properties_ids.append(property["id"])
                else:
                    continue

        return all_project_properties_ids

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns the json of a given resource-id.
    # Gets the id of the property as parameter
    def resource_json(self, resource_id):
        req = requests.get(f'{self.serverpath}/api/resourcetypes/{resource_id}?lang=all')
        resource_info = req.json()
        return resource_info

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns a Dict with the form: {property_id: info about property}. It contains all property-information of one project.
    # Gets the id of the property as parameter
    def all_prop_info(self, resource_info):
        all_prop_dict = {}

        for resource in resource_info:
            for property in resource_info[resource]["properties"]:
                if "id" in property:
                    if property["id"] not in all_prop_dict:
                        all_prop_dict.update({
                            property["id"]: property
                        })
                    else:
                        continue

        return all_prop_dict

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns all resources of a given project
    # It gets the json file of the resources of the current project as parameter.
    def project_resources(self, resource_types_json):
        all_project_resources_ids = []

        for resource_type_id in resource_types_json["resourcetypes"]:
            if resource_type_id["id"] not in all_project_resources_ids:
                all_project_resources_ids.append(property["id"])
            else:
                continue

        return all_project_resources_ids

    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns a dict with a mapping of the names of the ontology that needs to be used in the get(url)
    # Gets the current project id as parameter
    def name_mapper(self):
        name_map = {}
        req = requests.get(f'{self.serverpath}/api/vocabularies')
        vocabularies = req.json()

        req = requests.get(f'{self.serverpath}/api/projects')
        projects = req.json()


        for vocabulary in vocabularies["vocabularies"]:
            for project in projects["projects"]:
                if vocabulary["id"] == project["id"]:
                    name_map.update({
                        project["shortname"]: vocabulary["shortname"]
                    })
        return name_map
    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns a dict with all the resource-ids and the corresponding name {resource_id: resource_name} for the whole project
    # Gets all the resource id's of the project as parameter
    def resource_name(self, resource_info):
        resource_name_dict = {}

        for resource_id in resource_info:
            resource_name_dict.update({
                resource_id: resource_info[resource_id]["name"]
            })

        return resource_name_dict
    #-------------------------------------------------------------------------------------------------------------------
    # Function that returns a dict with all the resource-information {resource_id: resource_info} for the whole project
    # Gets all the resource id's of the project as parameter
    def resource_info(self, resource_ids):

        myResTypeInfo = {}
        for momResId in resource_ids:
            if int(momResId) == 153:
                continue# Error in Database. resource with id 153 gives an error
            resType = self.resource_json(momResId)
            myResTypeInfo[momResId] = resType["restype_info"]

        return myResTypeInfo

    # ==================================================================================================================
    # Function that assembles the Name of the property as well as adding for each property id that is in the project the
    # needed property fields
    # Gets all the property id's of the project as well as the property infos from the function all_prop_info
    def prop_name(self, property_ids, prop_info):

        for property_id in property_ids:
            # Getting framework for the Properties section of the ontology
            tmpOnto["project"]["ontologies"][0]["properties"].append({
                "name": prop_info[property_id]["name"],
                "super": [],
                "object": "",
                "labels": {},
                "comments": {},
                "gui_element": "",
                "gui_attributes": {}
            })

    #-------------------------------------------------------------------------------------------------------------------
    # Function that assembles the super of the property
    # Gets the property infos from the function all_prop_info and the supermap and objectmap as parameter
    def prop_super(self, prop_info, super_map, object_map):

        for property_element in tmpOnto["project"]["ontologies"][0]["properties"]:
            for specific_prop in prop_info:
                if prop_info[specific_prop]["name"] == property_element["name"]:
                    if prop_info[specific_prop]["vt_name"] is not super_map:
                        property_element["super"] = "hasValue"
                    else:
                        property_element["super"] = super_map[object_map[prop_info[specific_prop]["vt_name"]]]

    #-------------------------------------------------------------------------------------------------------------------
    # Function that assembles the object of the property
    # Gets the property infos from the function all_prop_info
    def prop_object(self, prop_info, resource_ids, recource_names, object_map):

        for property_element in tmpOnto["project"]["ontologies"][0]["properties"]:
            for specific_prop in prop_info:
                if prop_info[specific_prop]["name"] == property_element["name"]:
                    property_element["object"] = object_map[prop_info[specific_prop]["vt_name"]]

                    # From here on: special case treatment!
                    if property_element["object"] == "LinkValue":  # Determening ressource type of LinkValue (Bugfix)
                        resource_type_id = ""
                        if prop_info[specific_prop]["attributes"] is not None:
                            attributes = prop_info[specific_prop]["attributes"].split(";")
                            for attribute in attributes:
                                kv = attribute.split("=")
                                if kv[0] == "restypeid":
                                    resource_type_id = kv[1]

                        if resource_type_id == "":
                            property_element["object"] = "** FILL IN BY HAND **"
                        elif resource_type_id not in resource_ids:
                            property_element["object"] = "** FILL IN BY HAND (restypeid=0) **"

                        else:
                            property_element["object"] = recource_names[resource_type_id]

    # -------------------------------------------------------------------------------------------------------------------
    # Function that assembles the labels of the property
    # Gets the property infos from the function all_prop_info
    def prop_labels(self, prop_info):

        for property_element in tmpOnto["project"]["ontologies"][0]["properties"]:
            for specific_prop in prop_info:
                if prop_info[specific_prop]["name"] == property_element["name"]:
                    for label in prop_info[specific_prop]["label"]:
                        property_element["labels"].update({
                            label["shortname"]: label["label"]
                        })


    # -------------------------------------------------------------------------------------------------------------------
    # Function that assembles all the comments of the property
    # Gets the property infos from the function all_prop_info
    def prop_comments(self, prop_info):

        for property_element in tmpOnto["project"]["ontologies"][0]["properties"]:
            for specific_prop in prop_info:
                if prop_info[specific_prop]["name"] == property_element["name"]:
                    if prop_info[specific_prop]["description"] is not None:
                        for description in prop_info[specific_prop]["description"]:
                            property_element["comments"].update({
                                description["shortname"]: description["description"]
                            })


    # -------------------------------------------------------------------------------------------------------------------
    # Function that assembles the gui_element of the property
    # Gets the property infos from the function all_prop_info as well as the gui_element_map
    def prop_gui_element(self, prop_info, gui_element_map):

        for property_element in tmpOnto["project"]["ontologies"][0]["properties"]:
            for specific_prop in prop_info:
                if prop_info[specific_prop]["name"] == property_element["name"]:
                    property_element["gui_element"] = gui_element_map[prop_info[specific_prop]["gui_name"]]

    # -------------------------------------------------------------------------------------------------------------------
    # Function that assembles the gui_attributes of the property
    # Gets the property infos from the function all_prop_info
    def prop_gui_attributes(self, prop_info):

        for property_element in tmpOnto["project"]["ontologies"][0]["properties"]:
            for specific_prop in prop_info:
                if prop_info[specific_prop]["name"] == property_element["name"] and prop_info[specific_prop]["attributes"] is not None and prop_info[specific_prop]["attributes"] != '':
                    attribute_type = ""
                    attribute_value = 0

                    attribute_string = prop_info[specific_prop]["attributes"]  # A attributes_string might look like "size=60;maxlength=200"
                    comma_split = attribute_string.split(";")  # comma_split looks eg like: ["size"= 60, "maxlength"= 200]
                    for sub_splits in comma_split:
                        attribute_type, attribute_value = sub_splits.split("=")
                        if attribute_value.isdecimal():
                            attribute_value = int(attribute_value)
                        else:
                            attribute_value = str(attribute_value)

                        property_element["gui_attributes"].update({
                            attribute_type: attribute_value
                        })

    # ==================================================================================================================
    def fetchProperties(self, project):

        guiEleMap = {
            "text": "SimpleText",
            "textarea": "Textarea",
            "richtext": "Richtext",
            "": "Colorpicker",
            "date": "Date",
            "": "Slider",
            "geoname": "Geonames",
            "spinbox": "Spinbox",
            "": "Checkbox",
            "radio": "Radio",
            "": "List",
            "pulldown": "Pulldown",
            "hlist": "Pulldown",
            "searchbox": "Searchbox",
            "interval": "IntervalValue",
            "fileupload": "__FILEUPLOAD__"

        }  # Dict that maps the old guiname from salsa to the new guielement from knorapy

        objectMap = {
            "Text": "TextValue",
            "Richtext": "TextValue",
            "Iconclass": "TextValue",
            "": "ColorValue",
            "Date": "DateValue",
            "Time": "TimeValue",
            "Floating point number": "DecimalValue",
            "": "GeomValue",
            "Geoname": "GeonameValue",
            "Integer value": "IntValue",
            "": "BooleanValue",
            "": "UriValue",
            "": "IntervalValue",
            "Selection": "ListValue",
            "Hierarchical list": "ListValue",
            "Resource pointer": "LinkValue"
        }  # Dict that maps the old vt-name from salsa to the new Object type from knorapy
        # TODO right mapping from object map to super map
        superMap = {
            "": "hasValue",
            "LinkValue": "hasLinkTo",
            "ColorValue": "hasColor",
            "": "hasComment",
            "": "hasGeometry",
            "": "isPartOf",
            "": "isRegionOf",
            "": "isAnnotationOf",
            "": "seqnum"
        }  # Dict that maps the old the super corresponding to the object-type

        # ----------------------------------Assembly-------------------------------------

        req = requests.get(f'{self.serverpath}/api/resourcetypes/?vocabulary={self.name_list[project["shortname"]]}&lang=all')
        resource_json = req.json()

        resource_ids = self.res_ids(resource_json)
        resource_info = self.resource_info(resource_ids)
        resource_names = self.resource_name(resource_info)
        property_ids = self.prop_ids(resource_json)
        prop_info = self.all_prop_info(resource_info) #  is the map {property_id: info} with all the property_id's for 1 project.

        self.prop_name(property_ids, prop_info)
        self.prop_super(prop_info, superMap, objectMap)
        self.prop_object(prop_info, resource_ids, resource_names, objectMap)
        self.prop_labels(prop_info)
        self.prop_comments(prop_info)
        self.prop_gui_element(prop_info, guiEleMap)
        self.prop_gui_attributes(prop_info)

        # ----------------------------------Assembly-------------------------------------

    # ==================================================================================================================


if __name__ == '__main__':

    # This is a "blank" ontology. the json file is in the form we need in the new knora
    emptyOnto = {
        "prefixes": {},
        "project": {
            "shortcode": "",
            "shortname": "",
            "longname": "",
            "descriptions": {},
            "keywords": [],
            "lists": [],
            "groups": [],
            "users": [],
            "ontologies": [{
                "name": "",
                "label": "",
                "properties": [],
                "resources": []
            }]
        }
    }

    # Create an empty ontology
    tmpOnto = copy.deepcopy(emptyOnto)

    # Creating the ontology object. This object will create the new jsons.
    salsahJson = Converter()

    # Here the ontology object is being filled
    for projects in salsahJson.salsahJson["projects"]:
        # pprint("Making Deepcopy")
        tmpOnto = copy.deepcopy(
            emptyOnto)  # Its necessary to reset the tmpOnto for each project. Otherwhise they will overlap
        # pprint("FillShortLongName")
        salsahJson.fillShortLongName(projects)  # Fill the shortname as well as the longname into the empty ontology.
        # pprint("FillID")
        salsahJson.fillId(projects)  # Fill in the project id's (shortcode) to the corresponding projects.
        # pprint("FillDesc")
        salsahJson.fillDesc(projects)  # Fill in the vocabulary name and label
        # pprint("FillVocName")
        salsahJson.fillVocName(projects)  # Fill in the vocabulary name and label
        salsahJson.fetchKeywords(projects)  # Fills in the keywords of the corresponding project
        salsahJson.fetchLists(projects)
        # pprint("FetchRessources")
        salsahJson.fetchResources(projects)
        # pprint("FetchProperties")
        salsahJson.fetchProperties(projects)
        # Creating the new json files
        f = open("KAPPA" + projects["longname"] + ".json", 'w')
        f.write(json.dumps(tmpOnto, indent=4))
