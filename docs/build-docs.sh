cd source
python generate_rst.py
cd ..

make clean
make html
cp source/snet-cli-static/theme.css build/html/_static/css/

cd source
python generate_markdown.py ../build/html/ ../build/html/clean ../build/markdown
cd ..
rm -rf build/html/clean
