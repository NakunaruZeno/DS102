import numpy as np

def f(u):
    x, y = u
    return x**4 + y**4 - 4*x*y + 2

def grad(u):
    x, y = u
    return np.array([
        4 * x**3 - 4 * y,
        4 * y**3 - 4 * x
    ])

def hes(u):
    x, y = u
    return np.array([
        [12 * x**2, -4],
        [-4, 12 * y**2]
    ])

def newton_raphson(u_0, grad_fn, hes_fn, max_iter=100, epsilon=1e-4):
    u = u_0.astype(float)
    for _ in range(max_iter):
        grad = grad_fn(u)

        if np.linalg.norm(grad) < epsilon:
            return u

        hes = hes_fn(u)

        t = np.linalg.solve(hes, -grad)
        u = u + t

    return u

if __name__ == "__main__":
    u_0 = np.array([2, 2])
    u_optim = newton_raphson(u_0, grad, hes, max_iter=100)
    print("u_optim:", np.round(u_optim, 4))
    print("f(u_optim):", round(f(u_optim), 4))
