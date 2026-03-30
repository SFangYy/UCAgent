# Makefile for Formal Verification example

# First try ../../ucagent.py then fallback to system installed ucagent
UCAGENT_PY := $(wildcard ../../ucagent.py)

ifdef UCAGENT_PY
CMD ?= python3 ../../ucagent.py
else
CMD ?= ucagent
endif

clean:
	rm ./output -rf

init_%: 
	mkdir -p output
	cp -r rtls/$* output/
	@if [ ! -d output/$* ] || [ ! -f output/$*/__init__.py ]; then \
		if [ -f output/$*/$*.v ]; then \
			picker export output/$*/$*.v --rw 1 --sname $* --tdir output/ -c -w output/$*/$*.fst; \
		elif [ -f output/$*/$*.sv ]; then \
			picker export output/$*/$*.sv --rw 1 --sname $* --tdir output/ -c -w output/$*/$*.fst; \
		fi; \
	fi

mcp_%:  init_%
	$(CMD) output/ $* --config ./formal.yaml -s -hm --tui --mcp-server-no-file-tools --guid-doc-path ./FormalDoc/ --output unity_tests --mcp-server-port 5000 --master 127.0.0.1 --export-cmd-api ${ARGS}
