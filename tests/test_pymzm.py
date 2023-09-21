import unittest

import pymzm
import minizinc
import math

import inspect

import upymzm_equiv
from functools import partial

class TestPymzmProblems(unittest.TestCase):

    def setUp(self):
        self.model = pymzm.Model()
        self.gecode = minizinc.Solver.lookup("gecode")

    def test_ex1(self):
        model = self.model
        x = model.add_variable("x", -100, 100)
        model.add_constraint(1 * (x * x) + 4 * x == 0)
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()

        result = minizinc.Instance(self.gecode, model).solve(all_solutions=True)

        self.assertTrue(result.solution is not None)
        self.assertEqual(result[0, "x"], -4)
        self.assertEqual(result[1, "x"], 0)

    def test_ex2(self):
        model = self.model
        model.add_variable("x", 1, 10)
        model.add_constraint("(x mod 2) = 1")
        model.set_solve_method(pymzm.Method.int_search(["x"], "first_fail", "indomain_min"))
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()

        result = minizinc.Instance(self.gecode, model).solve(all_solutions=True)

        self.assertTrue(result.solution is not None)
        vals_expected = [1, 3, 5, 7, 9]
        for i in range(len(result)):
            self.assertEqual(vals_expected[i], result[i, "x"])

    def test_ex3(self):
        # https://www.minizinc.org/doc-2.5.5/en/modelling.html
        model = self.model
        nc = model.add_constant("nc", value=3)
        states = ["wa", "nsw", "nt", "v", "sa", "t", "q"]
        for state in states:
            model.add_variable(state, 1, nc.value)
        model.add_constraint("wa != nt")
        model.add_constraint("wa != sa")
        model.add_constraint("nt != sa")
        model.add_constraint("nt != q")
        model.add_constraint("sa != q")
        model.add_constraint("sa != nsw")
        model.add_constraint("sa != v")
        model.add_constraint("q != nsw")
        model.add_constraint("nsw != v")
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()

        result = minizinc.Instance(self.gecode, model).solve(all_solutions=True)
        
        self.assertTrue(result.solution is not None)
        self.assertEqual(18, len(result))

    def test_ex4_integer_factorization(self):
        model = self.model
        model.add_variable("x", 1, 99999999)
        model.add_variable("y", 1, 99999999)
        model.add_constraint(f"x * y = {7829 * 6907}")
        model.add_constraint("y > 1")
        model.add_constraint("x > y")
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()

        result = minizinc.Instance(self.gecode, model).solve(all_solutions=True)

        self.assertTrue(result.solution is not None)
        self.assertEqual(result[0].x, 7829)
        self.assertEqual(result[0].y, 6907)

    def test_ex5_nqueens(self):
        model = self.model
        n = 8
        q = model.add_variables("q", range(n), val_min=0, val_max=n-1)
        model.add_constraint(pymzm.Constraint.alldifferent(q))
        model.add_constraint(pymzm.Constraint.alldifferent([q[i] + i for i in range(n)]))
        model.add_constraint(pymzm.Constraint.alldifferent([q[i] - i for i in range(n)]))
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()

        result = minizinc.Instance(self.gecode, model).solve(all_solutions=True)

        self.assertTrue(result.solution is not None)
        self.assertEqual(92, len(result))

    def test_ex6_711(self):
        model = self.model
        n = 4
        items = model.add_variables("item", range(n), val_min=0, val_max=999)
        model.add_constraint(pymzm.Expression.sum(items) == 711)
        model.add_constraint(pymzm.Expression.product(items) == 711 * 100 * 100 * 100)
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()
        
        result = minizinc.Instance(self.gecode, model).solve(all_solutions=False)

        self.assertTrue(result.solution is not None)
        rs = [result[f"item_{i}"] / 100 for i in range(n)]
        self.assertTrue(sum(rs) == 7.11)
        self.assertTrue(math.prod(rs) == 7.11)

    def test_ex7_bibd(self):
        model = self.model
        # BIBD generation is described in most standard textbooks on combinatorics. 
        # A BIBD is defined as an arrangement of v  distinct objects into b blocks 
        # such that each block contains exactly k distinct objects, each object 
        # occurs in exactly r different blocks, and every two distinct objects 
        # occur together in exactly λ blocks.
        v = 7
        b = 7
        r = 3
        k = 3
        l = 1

        # Create a MiniZinc model
        xs = model.add_variables("x", indices=[(i, j) for i in range(v) for j in range(b)], vtype=pymzm.Variable.VTYPE_BOOL, val_min=0, val_max=1) # bool if object v is in block b

        for i in range(b):
            model.add_constraint(pymzm.Expression.sum(xs[i, j] for j in range(v)) == r)
        for i in range(v):
            model.add_constraint(pymzm.Expression.sum(xs[j, i] for j in range(b)) == k)

        for i in range(b):
            for j in range(i):
                model.add_constraint(pymzm.Expression.sum(xs[i, k] * xs[j, k] for k in range(v)) == l)

        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()
        
        result = minizinc.Instance(self.gecode, model).solve(all_solutions=False)

        self.assertTrue(result.solution is not None)

        for j in range(b):
            self.assertTrue(sum(result[f"x_{i}_{j}"] for i in range(v)) == r)
        for i in range(v):
            self.assertTrue(sum(result[f"x_{i}_{j}"] for j in range(b)) == r)
        # TODO add product between any pairs of rows
        for i in range(b):
            for j in range(i):
                self.assertTrue(sum(result[f"x_{i}_{k}"] * result[f"x_{j}_{k}"] for k in range(v)) == l)

class TestPymzmMisc(unittest.TestCase):
    def setUp(self):
        self.model = pymzm.Model()
        self.gecode = minizinc.Solver.lookup("gecode")

    def test_misc1(self):
        model = self.model
        # Negative summation
        xs = model.add_variables("x", range(10), 0, 1, vtype=pymzm.Variable.VTYPE_BOOL)
        ys = model.add_variables("y", range(10), 9, 10, vtype=pymzm.Variable.VTYPE_INTEGER)
        model.set_solve_criteria(pymzm.SOLVE_MAXIMIZE, pymzm.Expression.sum(xs) - pymzm.Expression.sum(ys))
        model.generate()
        
        result = minizinc.Instance(self.gecode, model).solve(all_solutions=False)

        self.assertTrue(result.solution is not None)
        self.assertTrue(result.objective < 0)


class TestExpression(unittest.TestCase):
    def setUp(self):
        self.solver = minizinc.Solver.lookup("gecode")
        self.val_min = -100
        self.val_max = 100

        self.model = pymzm.Model()
        self.x = self.model.add_variable("x", self.val_min, self.val_max)
        self.xs = self.model.add_variables("xs", range(10), self.val_min, self.val_max)


    
    def operator_case_single(self, func, positive_only=False, val_max: int=None):
        model = pymzm.Model()
        val_min = 0 if positive_only else self.val_min
        val_max = self.val_max if val_max is None else val_max
        
        x = model.add_variable("x", val_min, val_max)
        model.add_constraint(func(x))
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()

        sols = []
        for i in range(val_min, val_max + 1):
            try:
                if (func(i)):
                    sols.append(i)
            except ZeroDivisionError:
                pass
        #if (len(sols) == 0): print(inspect.getsource(func))

        results = minizinc.Instance(self.solver, model).solve(all_solutions=True)

        self.assertTrue(results.solution is not None)
        self.assertEqual(len(sols), len(results), f"{sols}, {results}")
        for i in range(len(results)):
            self.assertTrue(func(results[i, "x"]))
    
    def operator_case_multiple(self, func_expr, method_mz, method_py=None, var_count: int=5, is_solveable=True):
        model = pymzm.Model()
        
        xs = model.add_variables("x", range(var_count), self.val_min, self.val_max)

        func_mz = partial(func_expr, method_mz)
        func_py = partial(func_expr, method_py) if method_py is not None else None

        model.add_constraint(func_mz(xs))
        model.set_solve_criteria(pymzm.SOLVE_SATISFY)
        model.generate()

        result = minizinc.Instance(self.solver, model).solve(all_solutions=False)

        if (is_solveable):
            self.assertTrue(result.solution is not None)
            if (func_py is None):
                func_py = func_mz
            answ = func_py([result[f"x_{i}"] for i in range(var_count)])
            self.assertIsInstance(answ, bool) # for some reason non bools evaluate to true
            self.assertTrue(answ)     

    def test_operators_misc1(self):
        a=7
        b=3
        self.operator_case_single(lambda x: x == b)
        self.operator_case_single(lambda x: a + x == b)
        self.operator_case_single(lambda x: x + a == b)
        self.operator_case_single(lambda x: a - x == b)
        self.operator_case_single(lambda x: x - a == b)
        self.operator_case_single(lambda x: - x == b)
        self.operator_case_single(lambda x: - x == - b)
        self.operator_case_single(lambda x: 0 - (x - 5) == b)
        self.operator_case_single(lambda x: 0 - (x + 5) == b)
        self.operator_case_single(lambda x: - (x - 5) == b)
        self.operator_case_single(lambda x: - (x + 5) == b)
        self.operator_case_single(lambda x: a * x == b)
        self.operator_case_single(lambda x: x * a == b)
        self.operator_case_single(lambda x: a / x == b)
        #self.operator_case_single(lambda x: x / a == b) TODO: this isn't solved correctly in the mz solver
        self.operator_case_single(lambda x: a // x == b)
        self.operator_case_single(lambda x: x // a == b)
        self.operator_case_single(lambda x: a % x == b, positive_only=True)
        self.operator_case_single(lambda x: x % a == b, positive_only=True)

    def test_operators_misc2(self):
        self.operator_case_single(lambda x: x + (x + 7) == 21)
        self.operator_case_single(lambda x: x + (x - 7) == 21)
        self.operator_case_single(lambda x: x + (x * 7) == 21)
        self.operator_case_single(lambda x: x + (x * 7) == 40)
        self.operator_case_single(lambda x: x + (x / 7) == 21)
        #self.operator_case_single(lambda x: x + (x / 7) == 8)  TODO: this isn't solved correctly in the mz solver
        self.operator_case_single(lambda x: x + (x // 7) == 21)
        self.operator_case_single(lambda x: x + (x % 7) == 21)

        self.operator_case_single(lambda x: x - (x + 7) == 21)
        self.operator_case_single(lambda x: x - (x - 7) == 21)
        self.operator_case_single(lambda x: x - (x * 7) == 21)
        self.operator_case_single(lambda x: x - (x / 7) == 21)
        self.operator_case_single(lambda x: x - (x // 7) == 21)
        self.operator_case_single(lambda x: x - (x % 7) == 21)

        self.operator_case_single(lambda x: x * (x + 7) == 21)
        self.operator_case_single(lambda x: x * (x - 7) == 21)
        self.operator_case_single(lambda x: x * (x * 7) == 21)
        self.operator_case_single(lambda x: x * (x / 7) == 21)
        self.operator_case_single(lambda x: x * (x // 7) == 21)
        self.operator_case_single(lambda x: x * (x % 7) == 21)

        self.operator_case_single(lambda x: x / (x + 7) == 21)
        self.operator_case_single(lambda x: x / (x - 7) == 21)
        #self.operator_case_single(lambda x: x / (x * 7) == 21)
        #self.operator_case_single(lambda x: x / (x / 7) == 21)
        #self.operator_case_single(lambda x: x / (x // 7) == 21)
        #self.operator_case_single(lambda x: x / (x % 7) == 21)

        self.operator_case_single(lambda x: x // (x + 7) == 21)
        self.operator_case_single(lambda x: x // (x - 7) == 21)
        self.operator_case_single(lambda x: x // (x * 7) == 21)
        #self.operator_case_single(lambda x: x // (x / 7) == 21)
        self.operator_case_single(lambda x: x // (x // 7) == 21)
        self.operator_case_single(lambda x: x // (x % 7) == 21)

        #self.operator_case_single(lambda x: x % (x + 7) == 2)
        #self.operator_case_single(lambda x: x % (x - 7) == 2)
        #self.operator_case_single(lambda x: x % (x * 7) == 2)
        #self.operator_case_single(lambda x: x % (x / 7) == 2)
        #self.operator_case_single(lambda x: x % (x // 7) == 2)
        #self.operator_case_single(lambda x: x % (x % 7) == 2)

    def test_native_sum(self):
        self.operator_case_multiple(lambda f, xs: 0 + f(xs) == 27, sum, var_count=5)
        self.operator_case_multiple(lambda f, xs: 0 - f(xs) == 31, sum, var_count=5)
        self.operator_case_multiple(lambda f, xs: 5 * f(xs) == 30, sum, var_count=5)
        self.operator_case_multiple(lambda f, xs: f(xs) * f(xs) == 25, sum, var_count=2)
        self.operator_case_multiple(lambda f, xs: - f(xs) == 14, sum, var_count=5)

        expr = sum(self.xs)
        self.assertIsInstance(expr, pymzm.Expression)

    def test_sum(self):
        self.operator_case_multiple(lambda f, xs: 0 + f(xs) == 27, pymzm.Expression.sum, sum, var_count=5)
        self.operator_case_multiple(lambda f, xs: 0 - f(xs) == 31, pymzm.Expression.sum, sum, var_count=5)
        self.operator_case_multiple(lambda f, xs: 5 * f(xs) == 30, pymzm.Expression.sum, sum, var_count=5)
        self.operator_case_multiple(lambda f, xs: f(xs) * f(xs) == 25, pymzm.Expression.sum, sum, var_count=2)
        self.operator_case_multiple(lambda f, xs: - f(xs) == 14, pymzm.Expression.sum, sum, var_count=5)

        expr = pymzm.Expression.sum(self.xs)
        self.assertIsInstance(expr, pymzm.Expression)

    def test_product(self):
        self.operator_case_multiple(lambda f, xs: 0 + f(xs) == 2*1*1, pymzm.Expression.product, upymzm_equiv.Expression.product, var_count=3)
        self.operator_case_multiple(lambda f, xs: 0 - f(xs) == 5*6*(-3), pymzm.Expression.product, upymzm_equiv.Expression.product, var_count=3)
        self.operator_case_multiple(lambda f, xs: 5 * f(xs) == 11*5*1, pymzm.Expression.product, upymzm_equiv.Expression.product, var_count=3)
        self.operator_case_multiple(lambda f, xs: f(xs) + f(xs) == 2*11*6*2, pymzm.Expression.product, upymzm_equiv.Expression.product, var_count=3)
        self.operator_case_multiple(lambda f, xs: - f(xs) == 5*5*5, pymzm.Expression.product, upymzm_equiv.Expression.product, var_count=3)

        expr = pymzm.Expression.product(self.xs)
        self.assertIsInstance(expr, pymzm.Expression)

    def test_min(self):
        self.operator_case_multiple(lambda f, xs: f([*xs, 5]) == 5, pymzm.Expression.min, min, var_count=5)
        self.operator_case_multiple(lambda f, xs: f([*xs, 2]) == 5, pymzm.Expression.min, min, var_count=5, is_solveable=False)
        self.operator_case_multiple(lambda f, xs: f([*xs, 7]) == 5, pymzm.Expression.min, min, var_count=5)
        self.operator_case_multiple(lambda f, xs: f([*xs, -5]) == 5, pymzm.Expression.min, min, var_count=5, is_solveable=False)

        expr = pymzm.Expression.product(self.xs)
        self.assertIsInstance(expr, pymzm.Expression)

    def test_max(self):
        self.operator_case_multiple(lambda f, xs: f([*xs, 5]) == 5, pymzm.Expression.max, max, var_count=5)
        self.operator_case_multiple(lambda f, xs: f([*xs, 2]) == 5, pymzm.Expression.max, max, var_count=5, is_solveable=False)
        self.operator_case_multiple(lambda f, xs: f([*xs, 7]) == 5, pymzm.Expression.max, max, var_count=5, is_solveable=False)
        self.operator_case_multiple(lambda f, xs: f([*xs, -5]) == 5, pymzm.Expression.max, max, var_count=5, is_solveable=False)

        expr = pymzm.Expression.product(self.xs)
        self.assertIsInstance(expr, pymzm.Expression)

    def test_funcs_pow(self):
        self.operator_case_single(lambda x: pow(x, 2) == 81)
        self.operator_case_single(lambda x: pow(x, 2) == 5)
        self.operator_case_single(lambda x: pow(x, 3) == 27)
        self.operator_case_single(lambda x: pow(2, x) == 64, val_max=10)
        self.operator_case_single(lambda x: x ** 2 == 81)
        self.operator_case_single(lambda x: x ** 2 == 5)
        self.operator_case_single(lambda x: x ** 3 == 27)
        self.operator_case_single(lambda x: 3 ** x == 243, val_max=10)
        
        expr = pymzm.Expression.product(self.xs)
        self.assertIsInstance(expr, pymzm.Expression)

    def test_funcs_abs(self):
        self.operator_case_single(lambda x: abs(-x) == 81)
        self.operator_case_single(lambda x: -abs(x) == 5)
        self.operator_case_single(lambda x: abs(x) == 27)
        self.operator_case_single(lambda x: abs(x) == -27)

        expr = pymzm.Expression.product(self.xs)
        self.assertIsInstance(expr, pymzm.Expression)

    def test_add(self):
        self.operator_case_single(lambda x: x + x == 4)
        self.operator_case_single(lambda x: 5 + x == 4)
        self.operator_case_single(lambda x: x + 4 == 4)
        
        self.assertIsInstance(self.x + self.x, pymzm.Expression)
        self.assertIsInstance(5 + self.x, pymzm.Expression)
        self.assertIsInstance(self.x + 5, pymzm.Expression)

    def test_sub(self):
        self.operator_case_single(lambda x: x - x == 4)
        self.operator_case_single(lambda x: 5 - x == 4)
        self.operator_case_single(lambda x: x - 4 == 4)
        
        self.assertIsInstance(self.x - self.x, pymzm.Expression)
        self.assertIsInstance(5 - self.x, pymzm.Expression)
        self.assertIsInstance(self.x - 5, pymzm.Expression)

    def test_mul(self):
        self.operator_case_single(lambda x: x * x == 16)
        self.operator_case_single(lambda x: 5 * x == 10)
        self.operator_case_single(lambda x: x * 4 == 4)
        
        self.assertIsInstance(self.x * self.x, pymzm.Expression)
        self.assertIsInstance(5 * self.x, pymzm.Expression)
        self.assertIsInstance(self.x * 5, pymzm.Expression)

    def test_truediv(self):
        self.operator_case_single(lambda x: x / x == 1)
        self.operator_case_single(lambda x: 20 / x == 10)
        self.operator_case_single(lambda x: x / 2 == 4)
        
        self.assertIsInstance(self.x / self.x, pymzm.Expression)
        self.assertIsInstance(2 / self.x, pymzm.Expression)
        self.assertIsInstance(self.x / 2, pymzm.Expression)

    def test_floordiv(self):
        self.operator_case_single(lambda x: x // x == 1)
        self.operator_case_single(lambda x: 30 // x == 10)
        self.operator_case_single(lambda x: x // 4 == 4)
        
        self.assertIsInstance(self.x // self.x, pymzm.Expression)
        self.assertIsInstance(5 // self.x, pymzm.Expression)
        self.assertIsInstance(self.x // 5, pymzm.Expression)

    def test_mod(self):
        self.operator_case_single(lambda x: x % x == 0, positive_only=True)
        self.operator_case_single(lambda x: 5 % x == 2, positive_only=True)
        self.operator_case_single(lambda x: x % 4 == 3, positive_only=True)
        
        self.assertIsInstance(self.x % self.x, pymzm.Expression)
        self.assertIsInstance(5 % self.x, pymzm.Expression)
        self.assertIsInstance(self.x % 5, pymzm.Expression)

    def test_neg(self):
        self.operator_case_single(lambda x: - x == 16)
        self.operator_case_single(lambda x: - x == -3)
        
        self.assertIsInstance(-self.x, pymzm.Expression)

    



def testMethod():
    pass



if __name__ == "__main__":
    print("".join("\n" for _ in range(10)))
    unittest.main()