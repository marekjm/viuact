CXX=g++
CXXSTD=c++17
CXXFLAGS=-std=$(CXXSTD) \
		 -g \
		 -Wall \
		 -Werror \
		 -Wpedantic

LIBS=\
	 -lpthread \
	 -lwebsockets


all: webs

clean:
	rm -f webs

webs: webs.cpp protocol_lws_minimal_server_echo.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< $(LIBS)
