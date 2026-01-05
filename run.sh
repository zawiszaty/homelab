#!/bin/bash

cd ansible
ansible-playbook -i inventory.ini deploy.yml workers.yml --ask-pass --ask-become-pass