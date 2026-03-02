# Unreal To Godot Exporter

Unreal Engine 에셋을 Godot Engine으로 마이그레이션하는 Python 플러그인입니다.
glTF 2.0 포맷을 통해 **Static Mesh, Skeletal Mesh, Animation**을 Godot에서 바로 사용할 수 있도록 내보냅니다.

## 지원 에셋

| 에셋 타입 | 자동 포함 항목 |
|-----------|---------------|
| **Static Mesh** | Materials, Textures |
| **Skeletal Mesh** | Skeleton, Materials, Textures |
| **Animation Sequence** | Skeleton, Preview Mesh (선택) |

## 요구사항

- Unreal Engine 5.x
- 다음 플러그인이 활성화되어 있어야 합니다:
  - **Python Script Plugin** (PythonScriptPlugin)
  - **glTF Exporter** (GLTFExporter)
  - **Editor Scripting Utilities** (EditorScriptingUtilities)

## 설치

1. 이 저장소를 클론하거나 다운로드합니다
2. 폴더를 언리얼 프로젝트의 `Plugins/` 디렉토리에 복사합니다
   ```
   YourProject/
   └── Plugins/
       └── UnrealToGodotExporter/
           ├── UnrealToGodotExporter.uplugin
           └── Content/
               └── Python/
                   └── ...
   ```
3. 언리얼 에디터를 실행합니다
4. **Edit > Plugins**에서 "Unreal To Godot Exporter"를 검색하고 활성화합니다
5. 에디터를 재시작합니다

## 사용법

### 방법 1: Content Browser 우클릭
1. Content Browser에서 내보낼 에셋을 선택합니다
2. 우클릭 > **"Export to Godot"**
3. 출력 폴더를 선택하고 내보내기를 실행합니다

### 방법 2: Tools 메뉴
1. Content Browser에서 내보낼 에셋을 선택합니다
2. 상단 메뉴 **Tools > "Export to Godot (Selected Assets)"**

### 방법 3: Python 콘솔에서 직접 실행
```python
from unreal_to_godot.ui import quick_export
quick_export()
```

## 출력 구조

```
GodotExport/
├── manifest.json
├── StaticMeshes/
│   └── SM_Chair/
│       └── SM_Chair.glb
├── SkeletalMeshes/
│   └── SK_Character/
│       └── SK_Character.glb
└── Animations/
    └── Anim_Run/
        └── Anim_Run.glb
```

## Godot에서 가져오기

1. 내보낸 `.glb` 파일을 Godot 4.x 프로젝트의 파일시스템 패널에 드래그&드롭합니다
2. Godot가 자동으로 glTF를 인식하고 임포트합니다
3. 머티리얼, 텍스쳐, 스켈레톤이 모두 포함되어 있습니다

## Godot 호환성 설정

이 플러그인은 Godot에 최적화된 glTF 내보내기 설정을 자동 적용합니다:

| 설정 | 값 | 설명 |
|------|-----|------|
| Scale | 0.01 | UE cm → glTF/Godot meters 변환 |
| Normal Maps | 조정 활성화 | 그린채널 변환 (UE → glTF 규격) |
| Material Baking | 활성화 | UE 노드 그래프 → PBR 텍스쳐 변환 |
| Texture Format | PNG | 무손실 텍스쳐 |
| Skin Weights | 활성화 | 스켈레탈 메시 스키닝 |

## 알려진 제한사항

- Unreal의 IK/가상 본(IK_, VB_ 접두사)이 Godot에서도 보이지만 기능에는 영향 없음
- 별도 파일로 내보낸 애니메이션은 Godot에서 수동 매핑이 필요할 수 있음
- UE 머티리얼 노드 그래프는 베이킹을 통해 PBR 텍스쳐로 변환되므로 원본과 약간의 차이가 있을 수 있음

## 라이선스

MIT License
