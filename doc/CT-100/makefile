.PHONY: clean cleantmp all dvi ps pdf preview previewpdf previewps previewdvi cleanpix everything
LATEXMK=latexmk -e '$$pdflatex="pdflatex %O -shell-escape %S"; $$pdf_previewer="start evince %O %S"' -pdf

DOCNAME=kwapi-g5k


all: $(DOCNAME).pdf

clean:
	for E in aux fdb_latexmk log nav out pdf snm toc vrb pyg out.pyg ; do rm -f $(DOCNAME).$$E ; done

%.pdf: %.tex $(pixspdf)
	$(LATEXMK) $<

preview:
	$(LATEXMK) -pvc -view=pdf $(DOCNAME)
