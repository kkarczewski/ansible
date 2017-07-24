#! /usr/bin/env python

'''
@author: Kamil Karczewski
@project: Dabag
'''


ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': [''],
                    'supported_by': ''}
DOCUMENTATION = '''
---
module: xml_operation
short_description: Modyfing xml file from remote host
description:
  - Add new element or attribute to xml file
  - Modify value of element or attribute in xml file
  - Delete element or attribute in xml file
  - Add block of raw xml code to xml file
  - Rename tag name of element or attribute name in xml file
version_added: "1.0"
options:
  path:
     description:
       - full path to xml file
     required: true
     type: path
  xpath:
     description:
       - xpath to element or attribute in xml file
     required: true
     type: str
  state:
     description:
       - state defines what we want to do with xml file
     required: true
     choices: ['present','absent','addblock','rename']
     type: str
  value:
     description:
       - new value for new or modified element or attribute
     required: true
     type: str
requirements:
  - lxml
'''

EXAMPLES = '''
- name: Add xml element
  xml_operation:
    path: "{{path_xml}}"
    state: "present"
    xpath: "//business/beers/beer"
    value: "Beer added by Ansible"
- name: Add xml attribute
  xml_operation:
    path: "{{path_xml}}"
    state: "present"
    xpath: "//business/beers/beer[4]/@type"
    value: "Beer added by Ansible"
- name: Modify xml element
  xml_operation:
    path: "{{path_xml}}"
    state: "present"
    xpath: "//business/beers/beer[4]"
    value: "Beer edited by Ansible"
- name: Modify xml attribute
  xml_operation:
    path: "{{path_xml}}"
    state: "present"
    xpath: "//business/beers/beer[4]/@type"
    value: "Dark"
- name: Remove xml element
  xml_operation:
    path: "{{path_xml}}"
    state: "absent"
    xpath: "//business/beers/beer[4]"
- name: Remove xml attribute
  xml_operation:
    path: "{{path_xml}}"
    state: "absent"
    xpath: "//business/beers/beer[4]/@type"
- name: Add xml block of code
  xml_operation:
    path: "{{path_xml}}"
    state: "addblock"
    xpath: "//business/beers/beer[3]"
    value: "<beer type='jasne'>Beer in block of raw xml code</beer>"
- name: Rename xml element tag name
  xml_operation:
    path: "{{path_xml}}"
    state: "rename"
    xpath: "//business/beers/beer[4]"
    value: "beer_changed"
- name: Rename xml attribute name
  xml_operation:
    path: "{{path_xml}}"
    state: "rename"
    xpath: "//business/beers/beer[4]/@type"
    value: "type_changed"
'''

RETURN = '''
xml_file:
   description: new modified xml file
   returned: success
   type: xml tree
   sample: ./library/conf.xml
'''

import os
import sys
import argparse
try:
   from lxml import etree
except ImportError as e:
   print(e)
   print("There is no lxml installation.")
from ansible.module_utils.basic import *

def get_element(path, xpath):
   '''
   @path - path to xml file
   @xpath - xpath to element in xml tree
   Common function. Get xml file from path. Get root then get element from xpath.
   If wrong path there except IOError.
   '''
   try:
      tree = etree.parse(path)
      root = tree.getroot()
      element = root.xpath(xpath)
      if len(element) == 0:
         raise etree.XPathError('lxml.XpathError: Wrong XPath.')
      return element,root
   except IOError as e:
      print('Problem with file or filepath.')
      print(e)

def check_attrib(new_value, infile_value, new_element, infile_element, module):
   '''
   @new_value - new value for attribute
   @infile_value - value already in xml file
   @new_element - element specified in xpath (adding or modifing)
   @infile_element - element already in file (if exists)
   @module - ansible object used to print exists info
   Function to check if attribute with value exists. If exists print error, if not create it.
   '''
   if new_element in infile_element and new_value == infile_value:
      module.exit_json(
         changed=False,
         meta=['Element with value exists.',
               new_value, infile_value,
               new_element, infile_element]
      )
      return 1
   else:
      return 0

def check_element(xpath, value, root, module):
   '''
   @xpath - xpath to added or modified element
   @value - new value for element
   @root - full xml tree
   @module - ansible object used to print exists info
   Function to check if element with value exists. If exists print error, if not create it.
   '''
   if root.xpath(xpath+'[text()="'+value+'"]'):
      module.exit_json(
         changed=False,
         meta=['Element with value exists.', xpath, value]
      )
      return 1
   else:
      return 0

def check_block(value, root, module):
   '''
   @value - new value as block of xml code
   @root - full xml tree
   @module - ansible object used to print exists info
   Function to check if block of xml code exists. If exists print error, if not create it.
   '''
   if value in etree.tostring(root):
      module.exit_json(
         changed=False,
         meta=['Element with value exists.', etree.tostring(root)]
      )
      return 1
   else:
      return 0

def opt_present_attribute(value, path, xpath, module):
   '''
   @value - new value for modified element or attribute
   @xpath - xpath to modified element
   @path - path to xml file
   @module - ansible object used to print exists info
   Function to modifing argument's value or element's value on specified xpath.
   '''
   element,root = get_element(path, xpath.split('/@')[0])
   key = xpath.split('@')[1]
   if check_attrib(value, element[0].get(key) , key, element[0].keys(), module):
      element[0].set(key, value)
   else:
      element[0].set(key, value)
   etree.ElementTree(root).write(path, pretty_print=True)

def opt_present_element(value, xpath, path, module):
   '''
   @value - value for new element or attribute
   @xpath - xpath to element with new element at least
   @path - path to xml file
   @module - ansible object used to print exists info
   Function to create argument with value or element with value on specified xpath.
   '''
   specified_element = False
   element,root = get_element(path, xpath)
   if '[' in xpath:
      specified_element = True
   if check_element(xpath, value, root, module) or specified_element:
      element[0].text = value
   else:
      name_of_element = xpath[xpath.rfind('/')+1:]
      element,root = get_element(path, xpath[:xpath.rfind('/')])
      d = etree.SubElement(element[0], name_of_element)
      d.text = value
   etree.ElementTree(root).write(path, pretty_print=True)

def opt_del(xpath, path):
   '''
   @xpath - xpath to deleted element
   @path - path to xml file
   Function to delete argument or element even with subelements on specified xpath.
   '''
   if '@' in xpath:
      key = xpath.split('@')[1]
      element,root = get_element(path, xpath.split('/@')[0])
      element[0].attrib.pop(key)
   else:
      element,root = get_element(path, xpath)
      element[0].getparent().remove(element[0])
   etree.ElementTree(root).write(path, pretty_print=True)

def opt_add_block(value, xpath, path, module):
   '''
   @value - new value to add, specified as raw xml element
   @xpath - xpath to element, where we adding 
   @path - path to xml file
   @module - ansible object used to print exists info
   Function to add raw xml block in specified xpath.
   '''
   if '@' in xpath:
      raise Exception("You can't add block of raw xml as attribute value.")
   else:
      element,root = get_element(path, xpath)
      if check_block(value, root, module):
         sys.exit(1)
      else:
         parent = element[0].getparent()
         parent.insert(parent.index(element[0])+1, etree.XML(value))
         etree.ElementTree(root).write(path, pretty_print=True)

def opt_rename(value, xpath, path):
   '''
   @value - new tag name of element or attribute
   @xpath - xpath to element or attribute, where we change the name
   @path - path to xml file
   Function to rename element's tag name or attribute name.
   '''
   if '@' in xpath:
      element,root = get_element(path, xpath.split('/@')[0])
      old_key = xpath.split('/@')[1]
      old_value = element[0].attrib[old_key]
      element[0].attrib.pop(old_key)
      element[0].set(value, old_value)
   else:
      element,root = get_element(path, xpath)
      element[0].tag = value
   etree.ElementTree(root).write(path, pretty_print=True)

def main():

   fields = {
      "xpath": {"required": True, "type": "str"},
      "path": {"required": True, "type": "path" },
      "value": {"required": False, "type": "str"},
      "state": {
         "required": True,
         "type": "str",
         "choices": ['present','absent','addblock','rename']
      }
   }

   module = AnsibleModule(
      argument_spec = fields,
      supports_check_mode = True
   )
   if module.check_mode:
      module.exit_json(changed=False, meta=module.params)

   args = module.params
   if not args:
      module.fail_json(rc=256, msg="Problem with arguments")

   if args['state'] == 'present' and args['value']:
      if '@' in args['xpath']:
         opt_present_attribute(args['value'], args['path'], args['xpath'], module)
      else:
         opt_present_element(args['value'], args['xpath'], args['path'], module)
   elif args['state'] == 'absent':
      opt_del(args['xpath'], args['path'])
   elif args['state'] == 'addblock':
      if args['value']:
         opt_add_block(args['value'], args['xpath'], args['path'], module)
      else:
         raise Exception("ERROR: --value argument is required for -o modify") 
   elif args['state'] == 'rename':
      if args['value']:
         opt_rename(args['value'], args['xpath'], args['path'])
      else:
         raise Exception("ERROR: --value argument is required for -o rename")
   else:
      raise Exception("Wrong state")

   module.exit_json(changed=True, meta=module.params)

if __name__ == '__main__':
   main()
