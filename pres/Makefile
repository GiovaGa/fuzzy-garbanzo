.PHONY: all build clean view

# Target: Build the presentation PDF
all: build

build: pres.pdf

# Build from parent directory to resolve paths correctly
# pdflatex may return non-zero exit codes due to warnings, so we suppress them
pres.pdf: pres.tex
	@cd .. && pdflatex -interaction=nonstopmode -output-directory=pres pres/pres.tex > /dev/null 2>&1 || true
	@cd .. && pdflatex -interaction=nonstopmode -output-directory=pres pres/pres.tex > /dev/null 2>&1 || true

# Target: View the PDF (requires a PDF viewer)
view: pres.pdf
	xdg-open pres.pdf

# Target: Clean up build artifacts
clean:
	rm -f pres.aux pres.log pres.nav pres.out pres.snm pres.toc pres.pdf

.PHONY: all build clean view
