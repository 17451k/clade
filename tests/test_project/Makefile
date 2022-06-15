all:
	gcc zero.c main.c -o tmp_main -D TEST_MACRO -O3
	mv tmp_main main
	gcc zero.c main.c -o /dev/null -fsyntax-only
	gcc zero.c -M -MF zero.txt
	-clang -cc1 /dev/null
	gcc -c zero.c main.c
	gcc zero.o main.o -o main
	-as empty.s -o zero.o -I /usr/include
	-ar rcs zero.a zero.o main.o
	-objcopy main.o --strip-all
	-objcopy main.o zero.o --strip-all
	-ld main.o -o main.o2 -g -l interceptor -linterceptor -L../../clade/intercept -L clade/intercept
	-rm main zero.txt zero.o* main.o* zero.a
	g++ zero.c main.c -o /dev/null -D TEST_MACRO -O3
	-ccache gcc zero.c -I --ccache-skip /usr/include
	-ccache g++ zero.c -o /dev/null
