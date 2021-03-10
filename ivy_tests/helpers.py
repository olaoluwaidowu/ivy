"""
Collection of helpers for ivy unit tests
"""

# global
import ast
import ivy
try:
    import numpy as _np
    from ivy import numpy as _ivy_np
except ImportError:
    _np = None
    _ivy_np = None
try:
    import jax.numpy as _jnp
    from ivy import jax as _ivy_jnp
except ImportError:
    _jnp = None
    _ivy_jnp = None
try:
    import tensorflow as _tf
    _tf_version = float('.'.join(_tf.__version__.split('.')[0:2]))
    if _tf_version >= 2.3:
        # noinspection PyPep8Naming,PyUnresolvedReferences
        from tensorflow.python.types.core import Tensor as tensor_type
    else:
        # noinspection PyPep8Naming
        # noinspection PyProtectedMember,PyUnresolvedReferences
        from tensorflow.python.framework.tensor_like import _TensorLike as tensor_type
    physical_devices = _tf.config.list_physical_devices('GPU')
    for device in physical_devices:
        _tf.config.experimental.set_memory_growth(device, True)
    from ivy import tensorflow as _ivy_tf
except ImportError:
    _tf = None
    _ivy_tf = None
try:
    import torch as _torch
    from ivy import torch as _ivy_torch
except ImportError:
    _torch = None
    _ivy_torch = None
try:
    import mxnet as _mx
    import mxnet.ndarray as _mx_nd
    import mxnet.symbol as _mx_sym
    from ivy import mxnd as _ivy_mxnd
    from ivy import mxsym as _ivy_mxsym
except ImportError:
    _mx = None
    _mx_nd = None
    _mx_sym = None
    _ivy_mxnd = None
    _ivy_mxsym = None

_ivy_fws_dict = {'numpy': _ivy_np,
                 'jax': _ivy_jnp,
                 'tensorflow': _ivy_tf,
                 'tensorflow_graph': _ivy_tf,
                 'torch': _ivy_torch,
                 'mxnd': _ivy_mxnd,
                 'mxsym': _ivy_mxsym}

_iterable_types = [list, tuple, dict]
_excluded = []


def _convert_vars(vars_in, from_type, to_type_callable=None, to_type_attribute_method_str=None,
                  keep_other=True, to_type=None):
    new_vars = list()
    for var in vars_in:
        if type(var) in _iterable_types:
            return_val = _convert_vars(var, from_type, to_type_callable, to_type_attribute_method_str)
            new_vars.append(return_val)
        elif isinstance(var, from_type):
            if isinstance(var, _np.ndarray):
                if var.dtype == _np.float64:
                    var = var.astype(_np.float32)
                if bool(sum([stride < 0 for stride in var.strides])):
                    var = var.copy()
            if to_type_callable:
                new_vars.append(to_type_callable(var))
            elif to_type_attribute_method_str:
                new_vars.append(getattr(var, to_type_attribute_method_str)())
            else:
                raise Exception('Invalid. A conversion callable is required.')
        elif to_type is not None and isinstance(var, to_type):
            new_vars.append(var)
        elif keep_other:
            new_vars.append(var)

    return new_vars


def mx_sym_to_key(mx_sym):
    return list(mx_sym.attr_dict().keys())[0]


def mx_sym_to_val(mx_sym):
    return _mx.nd.array(ast.literal_eval(list(mx_sym.attr_dict().values())[0]['__init__'])[1]['value'])


def _get_mx_sym_args(args_list_in):
    new_vars = list()
    for i, arg in enumerate(args_list_in):
        if type(arg) in _iterable_types:
            new_vars += _get_mx_sym_args(arg)
        elif isinstance(arg, _mx_sym.Symbol):
            new_vars += [arg]
    return new_vars


def np_call(func, *args, **kwargs):
    return func(*args, **kwargs)


def jnp_call(func, *args, **kwargs):
    new_args = _convert_vars(args, _np.ndarray, _jnp.asarray)
    new_kw_vals = _convert_vars(kwargs.values(), _np.ndarray, _jnp.asarray)
    new_kwargs = dict(zip(kwargs.keys(), new_kw_vals))
    output = func(*new_args, **new_kwargs)
    if isinstance(output, tuple):
        return tuple(_convert_vars(output, _jnp.ndarray, _np.asarray))
    else:
        return _convert_vars([output], _jnp.ndarray, _np.asarray)[0]


def tf_call(func, *args, **kwargs):
    new_args = _convert_vars(args, _np.ndarray, _tf.convert_to_tensor)
    new_kw_vals = _convert_vars(kwargs.values(), _np.ndarray, _tf.convert_to_tensor)
    new_kwargs = dict(zip(kwargs.keys(), new_kw_vals))
    output = func(*new_args, **new_kwargs)
    if isinstance(output, tuple):
        return tuple(_convert_vars(output, tensor_type, _np.asarray))
    else:
        return _convert_vars([output], tensor_type, _np.asarray)[0]


def tf_graph_call(func, *args, **kwargs):
    new_args = _convert_vars(args, _np.ndarray, _tf.convert_to_tensor)
    new_kw_vals = _convert_vars(kwargs.values(), _np.ndarray, _tf.convert_to_tensor)
    new_kwargs = dict(zip(kwargs.keys(), new_kw_vals))

    @_tf.function
    def tf_func(*local_args, **local_kwargs):
        return func(*local_args, **local_kwargs)

    output = tf_func(*new_args, **new_kwargs)
    if isinstance(output, tuple):
        return tuple(_convert_vars(output, tensor_type, _np.asarray))
    else:
        return _convert_vars([output], tensor_type, _np.asarray)[0]


def torch_call(func, *args, **kwargs):
    new_args = _convert_vars(args, _np.ndarray, _torch.from_numpy)
    new_kw_vals = _convert_vars(kwargs.values(), _np.ndarray, _torch.from_numpy)
    new_kwargs = dict(zip(kwargs.keys(), new_kw_vals))
    output = func(*new_args, **new_kwargs)
    if isinstance(output, tuple):
        return tuple(_convert_vars(output, _torch.Tensor, lambda x: x.cpu().detach().numpy()))
    else:
        return _convert_vars([output], _torch.Tensor, lambda x: x.cpu().detach().numpy())[0]


def mx_call(func, *args, **kwargs):
    new_args = _convert_vars(args, _np.ndarray, _mx_nd.array)
    new_kw_items = _convert_vars(kwargs.values(), _np.ndarray, _mx_nd.array)
    new_kwargs = dict(zip(kwargs.keys(), new_kw_items))
    output = func(*new_args, **new_kwargs)
    if isinstance(output, tuple):
        return tuple(_convert_vars(output, _mx_nd.ndarray.NDArray, to_type_attribute_method_str='asnumpy'))
    else:
        return _convert_vars([output], _mx_nd.ndarray.NDArray, to_type_attribute_method_str='asnumpy')[0]


def mx_graph_call(func, *args, **kwargs):
    new_args = _convert_vars(args, _np.ndarray, _ivy_mxsym.array)
    new_kw_vals = _convert_vars(kwargs.values(), _np.ndarray, _ivy_mxsym.array)
    new_kwargs = dict(zip(kwargs.keys(), new_kw_vals))
    output_sym = func(*new_args, **new_kwargs)
    if output_sym is None:
        return

    mx_nd_args = _get_mx_sym_args(args)
    mx_nd_args += _get_mx_sym_args(list(kwargs.values()))

    mx_nd_keys = [mx_sym_to_key(item) for item in mx_nd_args]
    mx_nd_vals = [mx_sym_to_val(item) for item in mx_nd_args]
    mx_nd_dict = dict(zip(mx_nd_keys, mx_nd_vals))
    if len(mx_nd_dict) == 0:
        try:
            mx_nd_dict =\
            {list(output_sym.attr_dict().keys())[0]:
                 _mx.nd.array(ast.literal_eval(list(output_sym.attr_dict().values())[0]['__init__'])[1]['value'])}
        except KeyError:
            mx_nd_dict = dict()

    if isinstance(output_sym, tuple):
        output = [item.bind(_mx.cpu(), mx_nd_dict).forward() for item in output_sym]
    else:
        output = output_sym.bind(_mx.cpu(), mx_nd_dict).forward()
    if len(output) > 1:
        return tuple(_convert_vars(output, _mx_nd.ndarray.NDArray, to_type_attribute_method_str='asnumpy'))
    else:
        return _convert_vars(output, _mx_nd.ndarray.NDArray, to_type_attribute_method_str='asnumpy')[0]


_calls = [np_call, jnp_call, tf_call, tf_graph_call, torch_call, mx_call, mx_graph_call]


def assert_compilable(func_name, lib):
    ivy.set_framework(lib)
    try:
        ivy.compile_fn(ivy.__dict__[func_name])
    except Exception as e:
        ivy.unset_framework()
        raise e
    ivy.unset_framework()


def exclude(exclusion_list):
    global _excluded
    _excluded = _excluded + list(set(exclusion_list) - set(_excluded))


def frameworks():
    return list(set([ivy_fw for fw_str, ivy_fw in _ivy_fws_dict.items()
                     if ivy_fw is not None and fw_str not in _excluded]))


def calls():
    return [call for (fw_str, ivy_fw), call in zip(_ivy_fws_dict.items(), _calls)
            if ivy_fw is not None and fw_str not in _excluded]


def f_n_calls():
    return [(ivy_fw, call) for (fw_str, ivy_fw), call in zip(_ivy_fws_dict.items(), _calls)
            if ivy_fw is not None and fw_str not in _excluded]
