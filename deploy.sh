#!/bin/bash
ls | grep -v -e deploy.sh -e LICENSE.md -e venv | xargs rm -rf
git merge feat/post
source venv/bin/activate
make build
mv build/* .
rm -r build
git add .
git commit -m "automatically"
deactivate
