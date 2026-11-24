# CICD

GitHub ActionsとOIDCを使用し、`main`へのpushをトリガーにPythonコンテナをECRへpushし、ECSサービスへデプロイします。

## Workflows

### pr-check.yaml

Pull Request時にユニットテストとPR本文の必須項目を検証します。

### deploy.yaml

`main`へのpushまたは手動実行で以下を実行します。

1. ユニットテストを実行
2. コミットSHAをタグにしてDockerイメージをビルドし、ECRへpush
3. ECSタスク定義のイメージを置換して新リビジョンを登録
4. ECSサービスを更新し、安定するまで待機

## GitHub設定

リポジトリの **Settings → Secrets and variables → Actions** に設定します。

| 種別 | 名前 | 内容 |
|---|---|---|
| Secret | `AWS_ROLE_ARN` | GitHub OIDCで引き受けるIAMロールARN |
| Variable | `AWS_REGION` | 例: `ap-northeast-1` |
| Variable | `ECR_REPOSITORY` | ECRリポジトリ名 |
| Variable | `ECS_CLUSTER` | ECSクラスター名 |
| Variable | `ECS_SERVICE` | ECSサービス名 |
| Variable | `ECS_TASK_DEFINITION_FAMILY` | 初期タスク定義のファミリー名 |
| Variable | `CONTAINER_NAME` | タスク定義内のコンテナ名（既定: `app`） |

OIDC信頼ポリシーの`sub`は少なくとも以下のいずれかへ限定します。

```text
repo:Daisuke-Sato-690/ctcsfg-tec-02:ref:refs/heads/main
```

`production` Environmentを作成すると承認ゲートを設定できます。

## AWS設定

- `token.actions.githubusercontent.com`のOIDCプロバイダーを作成
- OIDCロールへECR push、ECSタスク定義登録・更新権限、`iam:PassRole`を付与
- ECRリポジトリとECSクラスター/サービスを作成
- タスク実行ロールへ`AmazonECSTaskExecutionRolePolicy`を付与
- CloudWatchロググループ`/ecs/my-app`を作成
- ALBターゲットグループのヘルスチェックパスを`/health`、ターゲットタイプを`ip`に設定

初回タスク定義のコンテナ名は`app`、コンテナポートは`8000`にします。デプロイ時は`ECS_TASK_DEFINITION_FAMILY`で指定した現在のタスク定義を取得し、イメージだけコミットSHAのタグへ置換します。
