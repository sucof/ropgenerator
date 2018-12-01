#include "Expression.hpp"
////////////////////////////////////////////////////////////////////////
int main(){
    // Test function 
    ExprObjectPtr e1,e2,e3,e4, e5; 
    ExprObjectPtr res; 
    
    e1 = ExprObjectPtr(new ExprObject (ExprPtr(new ExprCst(23, 64))));
    e2 = ExprObjectPtr(new ExprObject (ExprPtr(new ExprReg(0,64))));
    e5 = ExprObjectPtr(new ExprObject (ExprPtr(new ExprReg(3,64))));
    e4 = ExprObjectPtr(new ExprObject (ExprPtr(new ExprCst(6, 64))));
    e3 = e1 + (e2+e4) - e5*e4;
    //e3 = e1 +(e2+e4);
    cout << e3 << endl; 
    e3->simplify(); 
    cout << e3 << endl; 
    
    e1 = ExprObjectPtr(new ExprObject (ExprPtr(new ExprCst(31, 8))));
    e2 = Extract(e1, 2,0);
    e2->simplify();
    cout << e2 << endl;
    return 0;  
}
