# msb/base/data.py
from abc import ABC
from typing import Dict, Any, Optional, List, Union, Tuple, Callable, Iterator
from common.base.basecontainer import BaseContainer
from common.base.baseentity import BaseEntity
from common.utils.logging_setup import logger
import numpy as np
from pathlib import Path
from copy import deepcopy
from datetime import datetime
try:
    import pandas as pd
except ImportError:
    pd = None

class Series(BaseEntity, ABC):
    """Pandas-inspired Series class representing a single column of a Data object."""
    _data: 'Data'
    _field: str

    def __init__(self, name: str, data: 'Data', field: str, isactive: bool = True):
        self._data = data
        self._field = field
        super().__init__(name=name, data=data[field], isactive=isactive)
        logger.debug(f"Initialized Series '{name}' for field '{field}' in Data '{data.name}'")

    def filter(self, condition: Callable[[Any], bool]) -> 'Series':
        """Filter series based on a callable condition, returning a new Series."""
        mask = np.array([condition(val) for val in self.data], dtype=bool)
        filtered_data = self.data[mask]
        new_data = Data(
            name=f"{self._data.name}_filtered",
            field_names=[self._field],
            metadata=deepcopy(self._data.metadata),
            use_cache=self._data.use_cache,
            use_memmap=self._data._memmap
        )
        new_data.append([(val,) for val in filtered_data])
        new_series = Series(name=self.name, data=new_data, field=self._field, isactive=self.isactive)
        logger.debug(f"Filtered Series '{self.name}' to {len(filtered_data)} entries")
        return new_series

    def describe(self) -> Dict[str, Any]:
        """Generate descriptive statistics for the series."""
        try:
            values = np.array(self.data, dtype=float)
            return {
                'count': len(values),
                'mean': np.mean(values) if len(values) > 0 else np.nan,
                'std': np.std(values) if len(values) > 0 else np.nan,
                'min': np.min(values) if len(values) > 0 else np.nan,
                '25%': np.percentile(values, 25) if len(values) > 0 else np.nan,
                '50%': np.percentile(values, 50) if len(values) > 0 else np.nan,
                '75%': np.percentile(values, 75) if len(values) > 0 else np.nan,
                'max': np.max(values) if len(values) > 0 else np.nan
            }
        except (TypeError, ValueError):
            return {'count': len(self.data), 'unique': len(np.unique(self.data))}

    def info(self) -> Dict[str, Any]:
        """Return information about the series."""
        return {
            'type': 'Series',
            'name': self.name,
            'field': self._field,
            'size': len(self.data),
            'memory_usage': self.data.nbytes / (1024 ** 2) if not self._data._memmap else 'memmap',
            'parent_data': self._data.name
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Series to dictionary."""
        return {
            'type': 'Series',
            'name': self.name,
            'field': self._field,
            'data': list(self.data),
            'isactive': self.isactive
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], parent_data: 'Data') -> 'Series':
        """Create Series from dictionary."""
        return cls(
            name=data.get("name"),
            data=parent_data,
            field=data.get("field"),
            isactive=data.get("isactive", True)
        )

    def __eq__(self, other: Any) -> np.ndarray:
        return np.array([val == other for val in self.data], dtype=bool)

    def __getitem__(self, key: Union[int, slice, List[int]]) -> np.ndarray:
        return self.data[key]

    def __setitem__(self, key: Union[int, slice, List[int]], value: Any) -> None:
        self._data[self._field][key] = value
        logger.debug(f"Set values in Series '{self.name}' at key {key}")

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.data)

    def __str__(self) -> str:
        return f"Series('{self.name}', {len(self.data)} rows, field='{self._field}')"

    def __repr__(self) -> str:
        return self.__str__()

class Data(BaseContainer, ABC):
    """Pandas-inspired Data class for a structured NumPy array with arbitrary types.

    Supports dependencies, Pandas-like operations, and conversions to/from NumPy/Pandas.
    """
    data: np.ndarray
    metadata: Dict[str, Any]
    _memmap: Optional[Path]
    _field_names: List[str]

    def __init__(self, name: str = None, field_names: List[str] = None, metadata: Dict[str, Any] = None,
                 isactive: bool = True, use_cache: bool = True, use_memmap: Optional[Path] = None):
        self._memmap = use_memmap
        self._field_names = field_names or []
        if use_memmap and field_names:
            self.data = np.memmap(use_memmap, dtype=[(name, 'O') for name in self._field_names], mode='w+', shape=(0,))
        else:
            self.data = np.array([], dtype=[(name, 'O') for name in self._field_names] if self._field_names else [])
        self.metadata = metadata or {}
        if 'dependencies' not in self.metadata:
            self.metadata['dependencies'] = {}
        super().__init__(items={}, name=name, data=self.data, isactive=isactive, use_cache=use_cache)
        for field in self._field_names:
            self._items[field] = Series(name=field, data=self, field=field)
        logger.debug(f"Initialized Data '{name}' with fields {self._field_names}, memmap={self._memmap}")

    def append(self, rows: Union[Tuple[Any, ...], List[Tuple[Any, ...]]]) -> None:
        """Append one or multiple rows to the structured array."""
        if isinstance(rows, tuple):
            rows = [rows]
        if not rows:
            return
        if not self._field_names:
            self._field_names = [f'field_{i}' for i in range(len(rows[0]))]
            self.data = np.array([], dtype=[(name, 'O') for name in self._field_names])
            for field in self._field_names:
                self._items[field] = Series(name=field, data=self, field=field)
        elif len(rows[0]) != len(self._field_names):
            raise ValueError(f"Number of values ({len(rows[0])}) does not match number of fields ({len(self._field_names)})")

        new_shape = (len(self.data) + len(rows),)
        if self._memmap:
            new_data = np.memmap(self._memmap, dtype=self.data.dtype, mode='r+', shape=new_shape)
            if len(self.data) > 0:
                new_data[:len(self.data)] = self.data
            new_data[len(self.data):] = rows
            self.data = new_data
        else:
            new_data = np.zeros(new_shape, dtype=self.data.dtype)
            if len(self.data) > 0:
                new_data[:len(self.data)] = self.data
            new_data[len(self.data):] = rows
            self.data = new_data
        logger.debug(f"Appended {len(rows)} rows to Data '{self.name}', new size: {len(self.data)}")

    def filter(self, **filters) -> 'Data':
        """Filter data by conditions, returning a new Data object."""
        cache_key = tuple(sorted((k, str(v) if not callable(v) else id(v)) for k, v in filters.items()))
        if self.use_cache and hasattr(self, '_filter_cache') and cache_key in self._filter_cache:
            return self._filter_cache[cache_key]
        
        mask = np.ones(len(self.data), dtype=bool)
        for field, condition in filters.items():
            if field not in self._field_names:
                logger.warning(f"Field '{field}' not in Data '{self.name}', skipping filter")
                continue
            if callable(condition):
                mask &= np.array([condition(val) for val in self.data[field]], dtype=bool)
            else:
                mask &= self.data[field] == condition
        filtered_data = self.data[mask]
        
        new_data = Data(
            name=f"{self.name}_filtered",
            field_names=self._field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache,
            use_memmap=self._memmap
        )
        new_data.append([tuple(row[field] for field in self._field_names) for row in filtered_data])
        
        if self.use_cache:
            if not hasattr(self, '_filter_cache'):
                self._filter_cache = {}
            self._filter_cache[cache_key] = new_data
        logger.debug(f"Filtered Data '{self.name}' to {len(filtered_data)} entries")
        return new_data

    def loc(self, **filters) -> 'Data':
        return self.filter(**filters)

    def iloc(self, indices: Union[int, List[int], slice]) -> 'Data':
        filtered_data = self.data[indices]
        new_data = Data(
            name=f"{self.name}_iloc",
            field_names=self._field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache,
            use_memmap=self._memmap
        )
        new_data.append([tuple(row[field] for field in self._field_names) for row in filtered_data])
        logger.debug(f"Selected {len(filtered_data)} rows from Data '{self.name}' using iloc")
        return new_data

    def groupby(self, by: str) -> Dict[Any, 'Data']:
        if by not in self._field_names:
            raise ValueError(f"Field '{by}' not in Data '{self.name}'")
        cache_key = (by,)
        if self.use_cache and hasattr(self, '_groupby_cache') and cache_key in self._groupby_cache:
            return self._groupby_cache[cache_key]
        
        unique_values = np.unique(self.data[by])
        groups = {}
        for val in unique_values:
            mask = self.data[by] == val
            group_data = Data(
                name=f"{self.name}_group_{val}",
                field_names=self._field_names,
                metadata=deepcopy(self.metadata),
                isactive=self.isactive,
                use_cache=self.use_cache,
                use_memmap=self._memmap
            )
            group_data.append([tuple(row[field] for field in self._field_names) for row in self.data[mask]])
            groups[val] = group_data
        
        if self.use_cache:
            if not hasattr(self, '_groupby_cache'):
                self._groupby_cache = {}
            self._groupby_cache[cache_key] = groups
        logger.debug(f"Grouped Data '{self.name}' by '{by}' into {len(groups)} groups")
        return groups

    def sort(self, by: str, ascending: bool = True) -> 'Data':
        if by not in self._field_names:
            raise ValueError(f"Field '{by}' not in Data '{self.name}'")
        try:
            sorted_indices = np.argsort(self.data[by], kind='quicksort')
        except TypeError:
            sorted_indices = np.argsort([str(x) for x in self.data[by]], kind='quicksort')
        if not ascending:
            sorted_indices = sorted_indices[::-1]
        sorted_data = self.data[sorted_indices]
        
        new_data = Data(
            name=f"{self.name}_sorted",
            field_names=self._field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache,
            use_memmap=self._memmap
        )
        new_data.append([tuple(row[field] for field in self._field_names) for row in sorted_data])
        logger.debug(f"Sorted Data '{self.name}' by '{by}' in {'ascending' if ascending else 'descending'} order")
        return new_data

    def merge(self, other: 'Data', on: str, how: str = 'inner') -> 'Data':
        if on not in self._field_names or on not in other._field_names:
            raise ValueError(f"Field '{on}' not in both Data objects")
        merged_field_names = self._field_names + [f"{f}_other" for f in other._field_names if f != on]
        merged = Data(
            name=f"{self.name}_merged_{other.name}",
            field_names=merged_field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache
        )
        left = self.data
        right = other.data
        common = np.intersect1d(left[on], right[on])
        left_mask = np.isin(left[on], common)
        right_mask = np.isin(right[on], common)
        if how == 'inner':
            left_data = left[left_mask]
            right_data = right[right_mask]
        elif how == 'left':
            left_data = left
            right_mask = np.isin(right[on], left[on])
            right_data = right[right_mask]
        elif how == 'right':
            right_data = right
            left_mask = np.isin(left[on], right[on])
            left_data = left[left_mask]
        elif how == 'outer':
            all_values = np.union1d(left[on], right[on])
            left_mask = np.isin(left[on], all_values)
            right_mask = np.isin(right[on], all_values)
            left_data = left[left_mask]
            right_data = right[right_mask]
        else:
            raise ValueError(f"Unsupported merge type: {how}")
        
        new_data = np.zeros(len(left_data), dtype=[(f, 'O') for f in merged_field_names])
        for f in self._field_names:
            new_data[f] = left_data[f]
        for f in other._field_names:
            if f != on:
                new_data[f"{f}_other"] = right_data[f]
        merged.append([tuple(row[field] for field in merged_field_names) for row in new_data])
        logger.debug(f"Merged Data '{self.name}' with '{other.name}' on '{on}' using '{how}'")
        return merged

    def join(self, other: 'Data', on: Optional[str] = None, how: str = 'left') -> 'Data':
        if on is not None and (on not in self._field_names or on not in other._field_names):
            raise ValueError(f"Field '{on}' not in both Data objects")
        
        merged_field_names = self._field_names + [f"{f}_other" for f in other._field_names if on is None or f != on]
        joined = Data(
            name=f"{self.name}_joined_{other.name}",
            field_names=merged_field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache
        )
        
        if on is None:
            max_len = min(len(self.data), len(other.data)) if how in ['inner', 'left', 'right'] else max(len(self.data), len(other.data))
            new_data = np.zeros(max_len, dtype=[(f, 'O') for f in merged_field_names])
            if how == 'left' or how == 'inner':
                for f in self._field_names:
                    new_data[f][:len(self.data)] = self.data[f]
                for f in other._field_names:
                    new_data[f"{f}_other"][:min(len(other.data), max_len)] = other.data[f][:max_len]
            elif how == 'right':
                for f in self._field_names:
                    new_data[f][:min(len(self.data), max_len)] = self.data[f][:max_len]
                for f in other._field_names:
                    new_data[f"{f}_other"][:len(other.data)] = other.data[f]
            elif how == 'outer':
                for f in self._field_names:
                    new_data[f][:len(self.data)] = self.data[f]
                for f in other._field_names:
                    new_data[f"{f}_other"][:len(other.data)] = other.data[f]
            else:
                raise ValueError(f"Unsupported join type: {how}")
        else:
            return self.merge(other, on=on, how=how)
        
        joined.append([tuple(row[field] for field in merged_field_names) for row in new_data])
        logger.debug(f"Joined Data '{self.name}' with '{other.name}' on {on or 'index'} using '{how}'")
        return joined

    def pivot(self, index: str, columns: str, values: str) -> 'Data':
        if index not in self._field_names or columns not in self._field_names or values not in self._field_names:
            raise ValueError(f"One of index='{index}', columns='{columns}', values='{values}' not in Data '{self.name}'")
        
        index_values = np.unique(self.data[index])
        column_values = np.unique(self.data[columns])
        new_field_names = [index] + [f"{values}_{c}" for c in column_values]
        pivoted = Data(
            name=f"{self.name}_pivoted",
            field_names=new_field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache
        )
        
        rows = []
        for idx in index_values:
            row = [idx] + [None] * len(column_values)
            mask = self.data[index] == idx
            subset = self.data[mask]
            for i, col in enumerate(column_values):
                col_mask = subset[columns] == col
                if np.any(col_mask):
                    row[i + 1] = subset[values][col_mask][0]
            rows.append(tuple(row))
        
        pivoted.append(rows)
        logger.debug(f"Pivoted Data '{self.name}' on index='{index}', columns='{columns}', values='{values}'")
        return pivoted

    def pivot_table(self, index: str, columns: str, values: str, aggfunc: Union[str, Callable] = 'mean') -> 'Data':
        """Create a pivot table with aggregation, returning a new Data object.

        Args:
            index (str): Field to use as row index.
            columns (str): Field to use as column headers.
            values (str): Field containing values to aggregate.
            aggfunc (Union[str, Callable]): Aggregation function ('mean', 'sum', 'count', or callable).

        Returns:
            Data: New Data object with pivoted and aggregated data.
        """
        if index not in self._field_names or columns not in self._field_names or values not in self._field_names:
            raise ValueError(f"One of index='{index}', columns='{columns}', values='{values}' not in Data '{self.name}'")
        
        if aggfunc == 'mean':
            agg = np.mean
        elif aggfunc == 'sum':
            agg = np.sum
        elif aggfunc == 'count':
            agg = len
        elif callable(aggfunc):
            agg = aggfunc
        else:
            raise ValueError(f"Unsupported aggfunc: {aggfunc}")
        
        index_values = np.unique(self.data[index])
        column_values = np.unique(self.data[columns])
        new_field_names = [index] + [f"{values}_{c}" for c in column_values]
        pivoted = Data(
            name=f"{self.name}_pivot_table",
            field_names=new_field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache
        )
        
        rows = []
        for idx in index_values:
            row = [idx] + [None] * len(column_values)
            mask = self.data[index] == idx
            subset = self.data[mask]
            for i, col in enumerate(column_values):
                col_mask = subset[columns] == col
                if np.any(col_mask):
                    try:
                        row[i + 1] = agg(np.array(subset[values][col_mask], dtype=float))
                    except (TypeError, ValueError):
                        row[i + 1] = None
            rows.append(tuple(row))
        
        pivoted.append(rows)
        logger.debug(f"Created pivot table for Data '{self.name}' on index='{index}', columns='{columns}', values='{values}', aggfunc={aggfunc}")
        return pivoted

    def resample(self, time_field: str, rule: str, aggfunc: Union[str, Callable] = 'mean') -> 'Data':
        """Resample time-based data, returning a new Data object.

        Args:
            time_field (str): Field containing time values (must be astropy.Time or datetime).
            rule (str): Resampling rule (e.g., '1H' for hourly, '1D' for daily).
            aggfunc (Union[str, Callable]): Aggregation function ('mean', 'sum', 'count', or callable).

        Returns:
            Data: New Data object with resampled data.
        """
        if time_field not in self._field_names:
            raise ValueError(f"Time field '{time_field}' not in Data '{self.name}'")
        
        try:
            from astropy.time import Time
        except ImportError:
            Time = None
        
        if not all(isinstance(val, (Time, datetime)) for val in self.data[time_field] if val is not None):
            raise ValueError(f"Field '{time_field}' must contain astropy.Time or datetime objects")
        
        if aggfunc == 'mean':
            agg = np.mean
        elif aggfunc == 'sum':
            agg = np.sum
        elif aggfunc == 'count':
            agg = len
        elif callable(aggfunc):
            agg = aggfunc
        else:
            raise ValueError(f"Unsupported aggfunc: {aggfunc}")
        
        rule_map = {'S': 1, 'T': 60, 'H': 3600, 'D': 86400}
        unit = rule[-1]
        if unit not in rule_map:
            raise ValueError(f"Unsupported resampling rule: {rule}")
        freq = float(rule[:-1]) * rule_map[unit]
        
        times = np.array([t.mjd if isinstance(t, Time) else t.timestamp() / 86400 + 40587.0 for t in self.data[time_field]])
        min_time, max_time = np.min(times), np.max(times)
        bins = np.arange(min_time, max_time + freq / 86400, freq / 86400)
        
        new_data = Data(
            name=f"{self.name}_resampled",
            field_names=self._field_names,
            metadata=deepcopy(self.metadata),
            isactive=self.isactive,
            use_cache=self.use_cache
        )
        
        rows = []
        for i in range(len(bins) - 1):
            mask = (times >= bins[i]) & (times < bins[i + 1])
            if np.any(mask):
                row = []
                for field in self._field_names:
                    if field == time_field:
                        row.append(Time(bins[i], format='mjd') if Time else datetime.fromtimestamp(bins[i] * 86400 - 40587.0 * 86400))
                    else:
                        try:
                            row.append(agg(np.array(self.data[field][mask], dtype=float)))
                        except (TypeError, ValueError):
                            row.append(None)
                rows.append(tuple(row))
        
        new_data.append(rows)
        logger.debug(f"Resampled Data '{self.name}' on '{time_field}' with rule '{rule}'")
        return new_data

    def to_numpy(self, structured: bool = True) -> np.ndarray:
        """Convert Data to NumPy array.

        Args:
            structured (bool): If True, returns structured array; if False, returns 2D array.

        Returns:
            np.ndarray: Structured or 2D NumPy array.
        """
        logger.debug(f"Converted Data '{self.name}' to {'structured' if structured else '2D'} NumPy array")
        if structured:
            return self.data
        else:
            return np.array([list(row) for row in self.data], dtype=object)

    def to_pandas(self) -> 'pd.DataFrame':
        """Convert Data to pandas DataFrame.

        Returns:
            pandas.DataFrame: Converted DataFrame.
        """
        if pd is None:
            raise ImportError("pandas is not installed")
        try:
            from astropy.time import Time
        except ImportError:
            Time = None
        
        data = {
            field: [val.mjd if isinstance(val, Time) else val for val in self.data[field]]
            for field in self._field_names
        }
        df = pd.DataFrame(data)
        df.attrs['metadata'] = deepcopy(self.metadata)
        logger.debug(f"Converted Data '{self.name}' to pandas DataFrame")
        return df

    @classmethod
    def from_numpy(cls, array: np.ndarray, field_names: Optional[List[str]] = None, name: str = None,
                   metadata: Dict[str, Any] = None) -> 'Data':
        """Create Data from NumPy array.

        Args:
            array (np.ndarray): Structured or 2D NumPy array.
            field_names (List[str], optional): Names of fields (required for 2D array).
            name (str, optional): Name of the Data object.
            metadata (Dict[str, Any], optional): Metadata for the Data object.

        Returns:
            Data: New Data object.
        """
        if array.dtype.names is not None:
            # Structured array
            field_names = list(array.dtype.names)
            data = array
        else:
            # 2D array
            if field_names is None or len(field_names) != array.shape[1]:
                raise ValueError("field_names must match the number of columns in 2D array")
            data = np.array([tuple(row) for row in array], dtype=[(f, 'O') for f in field_names])
        
        instance = cls(name=name or "from_numpy", field_names=field_names, metadata=metadata or {})
        instance.append([tuple(row[field] for field in field_names) for row in data])
        logger.debug(f"Created Data '{instance.name}' from NumPy array with fields {field_names}")
        return instance

    @classmethod
    def from_pandas(cls, df: 'pd.DataFrame', name: str = None, metadata: Dict[str, Any] = None) -> 'Data':
        """Create Data from pandas DataFrame.

        Args:
            df (pandas.DataFrame): Input DataFrame.
            name (str, optional): Name of the Data object.
            metadata (Dict[str, Any], optional): Metadata for the Data object.

        Returns:
            Data: New Data object.
        """
        if pd is None:
            raise ImportError("pandas is not installed")
        try:
            from astropy.time import Time
        except ImportError:
            Time = None
        
        field_names = list(df.columns)
        rows = []
        for _, row in df.iterrows():
            processed_row = []
            for field in field_names:
                val = row[field]
                if isinstance(val, (pd.Timestamp, np.datetime64)) and 'time' in field.lower():
                    processed_row.append(Time(val.to_pydatetime()) if Time else val)
                else:
                    processed_row.append(val)
            rows.append(tuple(processed_row))
        
        instance = cls(name=name or "from_pandas", field_names=field_names, metadata=metadata or df.attrs.get('metadata', {}))
        instance.append(rows)
        logger.debug(f"Created Data '{instance.name}' from pandas DataFrame with fields {field_names}")
        return instance

    def add_dependency(self, field: str, depends_on: List[str]) -> None:
        if field not in self._field_names:
            raise ValueError(f"Field '{field}' not in Data '{self.name}'")
        for dep in depends_on:
            if dep not in self._field_names:
                raise ValueError(f"Dependency field '{dep}' not in Data '{self.name}'")
        self.metadata['dependencies'][field] = depends_on
        logger.debug(f"Added dependency for '{field}' on {depends_on} in Data '{self.name}'")

    def get_dependencies(self, field: str) -> List[str]:
        return self.metadata.get('dependencies', {}).get(field, [])

    def describe(self) -> Dict[str, Dict[str, Any]]:
        stats = {}
        for field in self._field_names:
            series = self[field]
            stats[field] = series.describe()
        return stats

    def info(self) -> Dict[str, Any]:
        return {
            'type': 'Data',
            'name': self.name,
            'size': len(self.data),
            'fields': self._field_names,
            'memory_usage': self.data.nbytes / (1024 ** 2) if not self._memmap else 'memmap',
            'memmap_path': str(self._memmap) if self._memmap else None,
            'metadata': self.metadata
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'Data',
            'name': self.name,
            'field_names': self._field_names,
            'data': [
                {field: val for field, val in zip(self._field_names, record)}
                for record in self.data
            ],
            'metadata': self.metadata,
            'isactive': self.isactive
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Data':
        instance = cls(
            name=data.get("name"),
            field_names=data.get("field_names", []),
            metadata=data.get("metadata", {}),
            isactive=data.get("isactive", True)
        )
        if data.get("data"):
            instance.append([tuple(record[field] for field in instance._field_names) for record in data["data"]])
        return instance

    def __getitem__(self, key: Union[str, List[str], slice, np.ndarray]) -> Union[Series, 'Data', np.ndarray]:
        if isinstance(key, str):
            if key not in self._items:
                self._items[key] = Series(name=key, data=self, field=key)
            return self._items[key]
        elif isinstance(key, (list, tuple)):
            new_field_names = [k for k in key if k in self._field_names]
            new_data = Data(
                name=f"{self.name}_subset",
                field_names=new_field_names,
                metadata=deepcopy(self.metadata),
                isactive=self.isactive,
                use_cache=self.use_cache,
                use_memmap=self._memmap
            )
            new_data.append([tuple(row[field] for field in new_field_names) for row in self.data])
            return new_data
        elif isinstance(key, (int, slice, list, np.ndarray)):
            if isinstance(key, np.ndarray) and key.dtype == bool:
                return self.filter(**{f"_mask_{id(self)}": lambda x: key})
            return self.iloc(key)
        raise KeyError(f"Invalid key type: {type(key)}")

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self._field_names:
            new_dtype = [(f, 'O') for f in self._field_names + [key]]
            new_data = np.zeros(len(self.data), dtype=new_dtype)
            for f in self._field_names:
                new_data[f] = self.data[f]
            new_data[key] = value
            self.data = new_data
            self._field_names.append(key)
            self._items[key] = Series(name=key, data=self, field=key)
        else:
            self.data[key] = value
        logger.debug(f"Set values for field '{key}' in Data '{self.name}'")

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator[Series]:
        return super().__iter__()

    def __str__(self) -> str:
        return f"Data('{self.name}', {len(self._field_names)} columns, {len(self)} rows)"

    def __repr__(self) -> str:
        return self.__str__()