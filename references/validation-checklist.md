# Validation Checklist

发布或修改本 Skill 后，至少检查这些点：

1. `SKILL.md` 有合法 YAML frontmatter。
2. `name` 为小写短横线格式。
3. `description` 明确说明这是通用购物决策 Skill。
4. 三个脚本都能独立运行：
   - `scripts/request_parser.py`
   - `scripts/shopping_link_builder.py`
   - `scripts/evaluate_candidates.py`
5. `sample-candidates.json` 是合法 JSON 数组。
6. 输出不会编造实时价格、销量、库存、店铺名或评价。
7. 最终建议必须给一个首选，而不是把选择权完全丢回用户。
8. 推荐结果需要包含下一步购买动作，例如搜索入口、商品入口或筛选规则。
