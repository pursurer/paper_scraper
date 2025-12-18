"""
字段提取器模块

从论文对象中提取指定字段，支持顶层字段和嵌套字段。
"""

from typing import List, Dict, Any, Optional, Union


class Extractor:
    """
    论文字段提取器
    
    从 OpenReview 论文对象中提取指定的字段，转换为扁平的字典格式。
    
    Attributes:
        fields: 要提取的顶层字段列表，如 ['forum', 'id']
        subfields: 要提取的嵌套字段，格式为 {父字段: [子字段列表]}
        include_subfield: 是否在结果中保留嵌套结构
        
    Example:
        >>> extractor = Extractor(
        ...     fields=['forum'],
        ...     subfields={'content': ['title', 'abstract', 'keywords', 'pdf']}
        ... )
        >>> paper_dict = extractor(paper_obj)
        >>> print(paper_dict)
        {'forum': 'abc123', 'title': 'My Paper', 'abstract': '...', ...}
    """
    
    def __init__(
        self,
        fields: List[str] = None,
        subfields: Dict[str, List[str]] = None,
        include_subfield: bool = False
    ):
        """
        初始化提取器。
        
        Args:
            fields: 要提取的顶层字段列表，如 ['forum', 'id']
            subfields: 要提取的嵌套字段，格式为 {父字段: [子字段列表]}
                      例如 {'content': ['title', 'abstract']}
            include_subfield: 是否在结果中保留嵌套结构
                             False（默认）: {'title': '...', 'abstract': '...'}
                             True: {'content': {'title': '...', 'abstract': '...'}}
        """
        self.fields = fields or []
        self.subfields = subfields or {}
        self.include_subfield = include_subfield
    
    def __call__(self, paper: Any) -> Dict[str, Any]:
        """
        使提取器可调用，等同于 extract() 方法。
        
        Args:
            paper: 论文对象（OpenReview Note 对象或类似结构）
            
        Returns:
            提取后的字典
        """
        return self.extract(paper)
    
    def extract(self, paper: Any) -> Dict[str, Any]:
        """
        从论文对象中提取指定字段。
        
        Args:
            paper: 论文对象，可以是：
                   - OpenReview Note 对象（有 __getattribute__ 方法）
                   - 字典
                   - 任何有对应属性的对象
            
        Returns:
            提取后的字典，包含所有指定的字段
            
        Example:
            >>> extractor = Extractor(
            ...     fields=['forum'],
            ...     subfields={'content': ['title', 'abstract']}
            ... )
            >>> result = extractor.extract(paper)
            >>> # result = {'forum': 'xxx', 'title': '...', 'abstract': '...'}
        """
        trimmed_paper = {}
        
        # 提取顶层字段
        for field in self.fields:
            trimmed_paper[field] = self._get_field_value(paper, field)
        
        # 提取嵌套字段
        for subfield_name, field_list in self.subfields.items():
            subfield_obj = self._get_field_value(paper, subfield_name)
            
            if self.include_subfield:
                # 保留嵌套结构
                trimmed_paper[subfield_name] = {}
                for field in field_list:
                    field_value = self._get_nested_field_value(subfield_obj, field)
                    trimmed_paper[subfield_name][field] = field_value
            else:
                # 扁平化：直接放到顶层
                for field in field_list:
                    field_value = self._get_nested_field_value(subfield_obj, field)
                    trimmed_paper[field] = field_value
        
        return trimmed_paper
    
    def _get_field_value(self, obj: Any, field: str) -> Any:
        """
        安全地获取对象的字段值。
        
        Args:
            obj: 源对象
            field: 字段名
            
        Returns:
            字段值，如果不存在则返回空字符串
        """
        if obj is None:
            return ''
        
        # 优先尝试字典方式
        if isinstance(obj, dict):
            return obj.get(field, '')
        
        # 尝试属性方式
        try:
            return getattr(obj, field, '')
        except Exception:
            return ''
    
    def _get_nested_field_value(self, subfield_obj: Any, field: str) -> Any:
        """
        安全地获取嵌套字段的值。
        
        Args:
            subfield_obj: 父字段对象（可能是字典或对象）
            field: 子字段名
            
        Returns:
            字段值，如果不存在则返回空字符串
        """
        if subfield_obj is None:
            return ''
        
        # 字典方式
        if isinstance(subfield_obj, dict):
            value = subfield_obj.get(field, '')
            # 处理 OpenReview 的 {value: "..."} 格式
            if isinstance(value, dict) and 'value' in value:
                return value['value']
            return value
        
        # 属性方式
        try:
            value = getattr(subfield_obj, field, '')
            # 处理 OpenReview 的 {value: "..."} 格式
            if isinstance(value, dict) and 'value' in value:
                return value['value']
            return value
        except Exception:
            return ''
    
    def __repr__(self) -> str:
        """返回提取器的字符串表示"""
        return (
            f"Extractor(fields={self.fields}, "
            f"subfields={self.subfields}, "
            f"include_subfield={self.include_subfield})"
        )

