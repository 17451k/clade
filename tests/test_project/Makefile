all:
	gcc zero.c main.c -o tmp_main -D TEST_MACRO -O3
	mv tmp_main main
	gcc zero.c main.c -o /dev/null
	gcc zero.c -M -MF zero.txt
	-clang -cc1 /dev/null
	gcc -c zero.c main.c
	gcc zero.o main.o -o main
	-rm main zero.txt zero.o* main.o*
