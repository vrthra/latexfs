# latexmount

The usage is as follows:

```
python3 -m pip install fusepy
python3 -m latexmount examples/main.tex
```

This will generate the following files

```
| ls -a examples/main.tex_mount                   
.     .tex      sec:approach.tex  sec:discussion.tex  sec:implementation.tex
..      _.tex     sec:background.tex  sec:evaluation.tex  sec:intro.tex
```

Each section is named using its label. For example, `sec:introduction.tex`
is labeled `sec:introduction`.

There two special files:

1. `.tex` is the regenerated TeX file from any modifications in the section
   files. All the sections are verbatim included in the file.
2. `_.tex` file is the same thing but the sections are simply
   added as `\include{section.tex}`.

Deleting a section is to simply delete the corresponding file. To add a section,
you have to add it in the `_.tex`.

After each modification, the original latex file is regenerated and written to
`<original>._` file. You can set the `TMP` value to empty string if you would
rather have this file overwrite your original file.
