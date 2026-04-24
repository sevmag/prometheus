---
name: normalize-numpy-docstrings
description: Normalize existing Python docstrings to NumPy style while preserving meaning and wording. Use when the user asks to normalize or clean up Python docstrings to NumPy style or current styling standards.
---

# Normalize NumPy docstrings
 
## When to use this skill
 
Use this skill whenever the user asks to  "normalize docstrings", "convert docstrings to NumPy style", "make docstrings consistent with style stadatards" or otherwise clean up Python docstrings.
 
## Instructions
 
When normalizing docstrings:
 
1. **Do not generate new docstrings**
  - If the object/class/method is missing a docstring entirely, do not generate one. This skill is only for normalizing existing docstrings.
 
2. **Preserve content and tone**
  - Do **not** change the high-level meaning or intent of the text.
  - Preserve informal or quirky phrasing where possible.
  - You may fix obviously broken grammar and typos.
  - You may perform stylistic fixes based on rules defined in `./agents/text-style-prometheus` skill.
 
3. **Structure docstrings in NumPy style**
  - Use the NumPy style guide: https://numpydoc.readthedocs.io/en/latest/format.html 
  - Keep or add a short one-line summary, sentence-cased and ending with a period.
  - Use these section headers when relevant:
    - `Parameters` for functions, `Attributes` for classes.
    - `Returns`
    - `Raises`
    - `Yields`
    - `Notes`
    - `Examples`
    - `See Also`
  - Format section headers **exactly** like:
    - `Parameters`
      `----------`
    - `Returns`
      `-------`
    - `Raises`
      `------`
    - etc.
 
4. **Summary line length**
  If the summary line exceeds the 79-character limit recommended by PEP 8, do not break the line with a new line. Keep the line long as is, otherwise the documentation generation tool will not render it correctly on the doc site.
  For example:
    - `Simulate the propagation of a particle and of any photons resulting from 
    the energy losses of this particle.` - the part after the line break ("the energy losses of this particle") does not render on the site.
    - `Simulate the propagation of a particle and of any photons resulting from the energy losses of this particle.` - the entire line renders on the site.

5. **Parameter entries**
  - For each parameter, use the pattern:
    - `name : type` or `name : type, optional`
  - Put the description on the next indented line(s).
  - Keep existing explanations; only adjust capitalization and punctuation as needed.
  - If the type is obvious from annotations or usage, include it (e.g. `list of Module`, `np.ndarray`, `str or None`).
  - For optional arguments already documented as optional (e.g. `rng` where default is set), add `, optional` to the type when appropriate.
 
6. **Returns entries**
  - If there is a single return value, use:
    - `name : type`
      `<indented sentence describing the value, starting with a capital letter and ending with a period.>`
  - If the function returns a bare value (e.g. `Detector`), you may use a short name like `det` or reuse the informal name already in the project (`detector`, `modules`, etc.).
 
7. **Raises entries**
  - For each exception, use:
    `ExceptionType`
    `   <indented sentence starting with "Raised if ..." or similar, capitalized and ending with a period.>`
    
    Example:
    ```python
    """
    IncompatibleSerialNumbersError
        Raised if serial numbers length doesn't match number of DOMs.
    """
    ```
  - Prefer "Raised if ..." or "Raised when ..." phrasing.

8. **General formatting rules for section blocks**
  - Within each Parameters / Returns / Raises / other section block, ensure every description starts with a capital letter and ends with a period.
    - Good example: `x : float` / `    X-position of the line.`
    - Avoid leading lowercase descriptions (e.g. `length of ...`); convert to `Length of ...`.

  - Maintain consistent type spellings that you have already used in this project, e.g.:
    - `np.ndarray`
    - `tuple of int`
    - `list of Module`
    - `Medium or None`
  
  - Enclose any references to code inside docstrings: variables, expressions, class names etc. into double backticks(``variable``). For example:
  ```python
  def t_geo(x, t_0, direc, x_0):
    """
    Calculate the expected arrival time of unscattered photons at position ``x``, emitted by a muon with direction ``direc`` and time ``t_0`` at position ``x_0``.
 
    Parameters
    ----------
    x : (3,1) np.ndarray
        Position of the sensor.
    t_0 : float
        Time at which the muon is at ``x_0``.
    direc : (3,1) np.ndarray
        Normalized direction vector of the muon.
    x_0 : (3, 1) np.ndarray
        Position of the muon at time ``t_0``.
    """
  ```

9. **What NOT to change**
  - Do **not** rename parameters or change function signatures.
  - Do **not** rewrite long narrative text beyond light capitalization/punctuation/typos fixes.
  - Do **not** "formalize" jokes or intentionally informal comments unless the user asks you to.
  - Do **not** generate docstrings for the objects that don't already have docstrings. 
 
 
## Examples from this project
 
- Constructor example:
 
```python
def __init__(self, modules: List[Module], medium: Union[Medium, None]):
    """Initialize detector.
 
    Parameters
    ----------
    modules : list of Module
        List of all the modules in the detector.
    medium : Medium or None
        Medium in which the detector is embedded.
    """
```
 
- Function with parameters, returns, and raises:
 
```python
def to_f2k(...):
    """Write detector corrdinates into f2k format.
 
    Parameters
    ----------
    geo_file : str
        File name of where to write it.
    serial_nos : list of str, optional
        Serial numbers for the optical modules. These MUST be in
        hexadecimal format, but there exact value does not matter. If
        nothing is provided, these values will be randomly generated.
    mac_ids : list of str, optional
        MAC (I don't think this is actually what this is called) IDs
        for the DOMs. By default these will be randomly generated. This
        is probably what you want to do.
 
    Raises
    ------
    IncompatibleSerialNumbersError
        Raised if serial numbers length doesn't match number of DOMs.
    IncompatibleMACIDsError
        Raised if MAC IDs length doesn't match number of DOMs.
    """
```