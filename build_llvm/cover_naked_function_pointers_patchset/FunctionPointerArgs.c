#include <stdio.h>
#include <stdlib.h>
#include <time.h>
// This is a program that dynamically assigns sections to a struct, which may contain function pointers.
// This is so when the structs are used it is impossible to know what is actually contained in them.
// 
// It is meant for the purpose of playground analysis with LLVM.


int globals_1 = 6;
int globals_2 = -3;

struct FunctionDescGeneric {
    int (*dispatcher)(struct FunctionDescGeneric*);
    int(*fn) (int, int, int);
    struct FunctionData *data;
};

struct FunctionData {
    int a;
    int b;
};


int function_one(int a, int b, int c) {
    globals_1 += a + b - c;
    return 0;
}

int function_two(int a, int b, int c) {
    globals_2 += (b - a) * c;
    return 1;
}


int FunctionOneDispatcher(struct FunctionDescGeneric *fnDesc){
    int a = fnDesc->data->a;
    int b = fnDesc->data->b;
    return fnDesc->fn(b, a, 10);
}

int FunctionTwoDispatcher(struct FunctionDescGeneric *fnDesc){
    int a = fnDesc->data->a;
    int b = fnDesc->data->b;
    return fnDesc->fn(a, b, -20);
}


void fill_data(struct FunctionDescGeneric *fnDesc,
    int(*dispatcher)(struct FunctionDescGeneric*),
    int(*fn)(int, int, int),
    struct FunctionData *data) {
    fnDesc->dispatcher = dispatcher;
    fnDesc->fn = fn;
    fnDesc->data = data;
}

void createFunctionOneData(struct FunctionDescGeneric *fnDesc) {
    struct FunctionData *data = malloc(sizeof(struct FunctionData));
    data->a = 4;
    data->b = 8;
    fill_data(fnDesc, FunctionOneDispatcher, function_one, data);
}

void createFunctionTwoData(struct FunctionDescGeneric *fnDesc) {
    struct FunctionData *data = malloc(sizeof(struct FunctionData));
    data->a = -3;
    data->b = 7;
    fill_data(fnDesc, FunctionTwoDispatcher, function_two, data);
}



// Don't care about the leakage
struct FunctionDescGeneric *getRandomStructOneOrTwo() {
    struct FunctionDescGeneric *fnDesc = malloc(sizeof(struct FunctionDescGeneric));
    if (time(NULL) % 2 == 0) {
        createFunctionOneData(fnDesc);
    } else{
        createFunctionTwoData(fnDesc);
    }
    return fnDesc;
}

void __sanitizer_cov_store_fun_pointer(unsigned storeAddr, unsigned storePosition){
    printf("storeAddr: %d storePosition: %d\n", storeAddr, storePosition);
}

int main(void) {
    struct FunctionDescGeneric *picked = getRandomStructOneOrTwo();
    int result = picked->dispatcher(picked);
    printf("chosen global variable=%d\nvalue of first global variable=%d\nvalue of first global variable=%d\n",result, globals_1, globals_2);
    free(picked);
    return 0;
}